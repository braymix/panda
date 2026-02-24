#!/usr/bin/env python3
"""
PANDA 3D — Analisi File STL
==============================

Analizza un file STL e produce un report con:
- Numero di triangoli
- Bounding box (min/max per ogni asse in mm)
- Verifica manifold (edge adjacency — bordi aperti = mesh non stampabile)
- Stima tempo di stampa (volume mesh * fattore infill)

Supporta sia STL ASCII che binario.

Uso:
  python3 analyze_stl.py modello.stl
  python3 analyze_stl.py modello.stl --infill 30
  python3 analyze_stl.py modello.stl --json
  python3 analyze_stl.py ~/panda/models/stl/*.stl   (analisi multipla)
"""

import argparse
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# STL parsing
# ---------------------------------------------------------------------------

def _parse_ascii_stl(content: str) -> list[tuple]:
    """Parsa STL ASCII. Ritorna lista di triangoli [(v0,v1,v2), ...]."""
    triangles = []
    current_verts = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("vertex "):
            parts = line.split()
            if len(parts) == 4:
                try:
                    current_verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    pass
        elif line.startswith("endfacet") or line.startswith("endloop"):
            if len(current_verts) == 3:
                triangles.append(tuple(current_verts))
                current_verts = []
    return triangles


def _parse_binary_stl(data: bytes) -> list[tuple]:
    """
    Parsa STL binario.
    Formato: 80 byte header | 4 byte uint32 n_triangles |
             n * (12 byte normal + 36 byte vertices + 2 byte attr)
    """
    if len(data) < 84:
        return []
    n_triangles = struct.unpack_from("<I", data, 80)[0]
    # Sanity check: ogni triangolo occupa 50 byte
    expected_size = 84 + n_triangles * 50
    if expected_size > len(data) + 1024:
        return []
    triangles = []
    offset = 84
    for _ in range(n_triangles):
        if offset + 50 > len(data):
            break
        v1 = struct.unpack_from("<fff", data, offset + 12)
        v2 = struct.unpack_from("<fff", data, offset + 24)
        v3 = struct.unpack_from("<fff", data, offset + 36)
        triangles.append((v1, v2, v3))
        offset += 50
    return triangles


def load_stl(path: Path) -> tuple[list, str]:
    """
    Carica un file STL (ASCII o binario).
    Ritorna (triangoli, formato) dove formato è "ascii" o "binary".
    """
    data = path.read_bytes()

    # Rileva ASCII: inizia con "solid" e contiene "vertex"
    try:
        header = data[:256].decode("ascii", errors="replace")
        if header.lstrip().startswith("solid") and b"vertex" in data:
            content = data.decode("ascii", errors="replace")
            tris = _parse_ascii_stl(content)
            if tris:
                return tris, "ascii"
    except Exception:
        pass

    # Binario (anche se il file inizia con "solid" — alcuni file binari lo fanno)
    tris = _parse_binary_stl(data)
    return tris, "binary"


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------

def compute_bounding_box(triangles: list) -> dict | None:
    """Calcola bounding box da tutti i vertici."""
    if not triangles:
        return None
    xs, ys, zs = [], [], []
    for tri in triangles:
        for v in tri:
            xs.append(v[0])
            ys.append(v[1])
            zs.append(v[2])
    return {
        "min_x": round(min(xs), 4), "max_x": round(max(xs), 4),
        "min_y": round(min(ys), 4), "max_y": round(max(ys), 4),
        "min_z": round(min(zs), 4), "max_z": round(max(zs), 4),
        "size_x": round(max(xs) - min(xs), 4),
        "size_y": round(max(ys) - min(ys), 4),
        "size_z": round(max(zs) - min(zs), 4),
    }


def check_manifold(triangles: list) -> dict:
    """
    Verifica manifold tramite edge adjacency.

    In un mesh manifold ogni edge è condiviso da esattamente 2 triangoli.
    - open_edges:        edge con 1 sola faccia adiacente → bordo aperto
    - non_manifold_edges: edge con 3+ facce → geometria non-manifold

    Usa arrotondamento a 6 decimali per gestire errori floating-point.
    """
    edge_count: dict[tuple, int] = defaultdict(int)

    for tri in triangles:
        # Normalizza ogni vertice a 6 cifre decimali per l'hash
        pts = [
            (round(v[0], 6), round(v[1], 6), round(v[2], 6))
            for v in tri
        ]
        # 3 edge del triangolo come coppia non-orientata (frozenset → tuple ordinata)
        for i in range(3):
            a, b = pts[i], pts[(i + 1) % 3]
            edge = (min(a, b), max(a, b))
            edge_count[edge] += 1

    open_edges        = sum(1 for c in edge_count.values() if c == 1)
    non_manifold_edges = sum(1 for c in edge_count.values() if c > 2)
    total_edges       = len(edge_count)
    is_manifold       = open_edges == 0 and non_manifold_edges == 0

    return {
        "is_manifold":         is_manifold,
        "open_edges":          open_edges,
        "non_manifold_edges":  non_manifold_edges,
        "total_edges":         total_edges,
    }


def compute_volume(triangles: list) -> float:
    """
    Calcola il volume del mesh usando il teorema della divergenza
    (somma dei volumi dei tetraedri firmati origine-triangolo).
    Funziona correttamente solo per mesh chiusi (manifold).
    """
    vol = 0.0
    for tri in triangles:
        v0, v1, v2 = tri
        # Prodotto misto: v0 · (v1 × v2) / 6
        vol += (
            v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
            + v1[0] * (v2[1] * v0[2] - v2[2] * v0[1])
            + v2[0] * (v0[1] * v1[2] - v0[2] * v1[1])
        ) / 6.0
    return abs(vol)


def estimate_print_time(volume_mm3: float, infill_pct: int = 20) -> dict:
    """
    Stima approssimativa del tempo di stampa FDM.

    Modello semplificato:
    - Volume efficace ≈ guscio esterno + infill × volume interno
    - Velocità stampa tipica: 50 mm/s, layer 0.2 mm, larghezza 0.4 mm
    - Fattore calibrato empiricamente: ~4 min/cm³ a 20% infill
    """
    vol_cm3 = volume_mm3 / 1000.0

    # Scala lineare con infill (0% → solo guscio ×0.4, 100% → pieno ×2.2)
    infill_factor = 0.4 + (infill_pct / 100.0) * 1.8
    minutes = vol_cm3 * 4.0 * infill_factor

    # Overhead fisso: riscaldamento + primo layer + fine stampa
    minutes += 4.0

    hours = int(minutes // 60)
    mins  = int(minutes % 60)

    return {
        "volume_cm3":        round(vol_cm3, 3),
        "infill_pct":        infill_pct,
        "estimated_minutes": round(minutes, 1),
        "estimated_human":   f"{hours}h {mins:02d}m" if hours > 0 else f"{mins}m",
        "note":              "Stima approssimativa ±50% — dipende da slicer, velocità, supporti",
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def analyze_file(stl_path: Path, infill_pct: int) -> dict:
    """Esegue tutti i check su un file STL e ritorna un dict con tutti i risultati."""
    stat = stl_path.stat()
    triangles, fmt = load_stl(stl_path)

    bb           = compute_bounding_box(triangles)
    manifold     = check_manifold(triangles) if triangles else None
    volume_mm3   = compute_volume(triangles) if triangles else 0.0
    print_est    = estimate_print_time(volume_mm3, infill_pct) if triangles else None

    return {
        "file":          str(stl_path),
        "format":        fmt,
        "size_bytes":    stat.st_size,
        "size_kb":       round(stat.st_size / 1024, 2),
        "triangles":     len(triangles),
        "bounding_box":  bb,
        "manifold":      manifold,
        "volume_mm3":    round(volume_mm3, 2),
        "print_estimate": print_est,
    }


def print_report(result: dict, verbose: bool = True):
    """Stampa il report in formato leggibile."""
    sep = "─" * 58
    path = Path(result["file"])

    print(f"\n{'═'*58}")
    print(f"  Analisi STL: {path.name}")
    print(f"{'═'*58}")
    print(f"  File:     {result['file']}")
    print(f"  Formato:  {result['format'].upper()}  |  {result['size_kb']:.1f} KB")
    print(f"  Triangoli: {result['triangles']:,}")

    # Bounding Box
    bb = result.get("bounding_box")
    if bb:
        print(f"\n  {sep}")
        print(f"  Bounding Box (mm):")
        print(f"    X:  {bb['min_x']:>10.3f}  →  {bb['max_x']:>10.3f}   ({bb['size_x']:.3f} mm)")
        print(f"    Y:  {bb['min_y']:>10.3f}  →  {bb['max_y']:>10.3f}   ({bb['size_y']:.3f} mm)")
        print(f"    Z:  {bb['min_z']:>10.3f}  →  {bb['max_z']:>10.3f}   ({bb['size_z']:.3f} mm)")
    else:
        print(f"\n  Bounding Box: N/D (nessun triangolo)")

    # Manifold
    m = result.get("manifold")
    if m:
        print(f"\n  {sep}")
        ok = m["is_manifold"]
        icon = "✓" if ok else "✗"
        label = "Mesh CHIUSO — stampabile" if ok else "Mesh NON manifold"
        print(f"  Manifold: {icon}  {label}")
        print(f"    Edge totali:         {m['total_edges']:>8,}")
        if m["open_edges"] > 0:
            print(f"    Bordi aperti (1 faccia):  {m['open_edges']:>5,}  ← problema")
        if m["non_manifold_edges"] > 0:
            print(f"    Edge non-manifold (3+ facce): {m['non_manifold_edges']:>3,}  ← problema")
        if not ok:
            print(f"\n  Suggerimenti repair:")
            print(f"    • Meshmixer → Analysis → Inspector → Auto-Repair")
            print(f"    • netfabb online: https://netfabb.autodesk.com")
            print(f"    • Rigenera il modello con PANDA a qualità 'high'")

    # Volume e stampa
    pe = result.get("print_estimate")
    if pe:
        print(f"\n  {sep}")
        print(f"  Volume mesh: {result['volume_mm3']:,.1f} mm³  ({pe['volume_cm3']:.2f} cm³)")
        print(f"\n  Stima stampa (infill {pe['infill_pct']}%, PLA, 50 mm/s):")
        print(f"    Tempo stimato:  {pe['estimated_human']}  (~{pe['estimated_minutes']:.0f} min)")
        print(f"    {pe['note']}")

    print(f"{'═'*58}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PANDA 3D — Analisi file STL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("stl_files", nargs="+", metavar="file.stl",
                        help="Uno o più file .stl da analizzare")
    parser.add_argument("--infill", type=int, default=20, metavar="N",
                        help="Percentuale infill per la stima di stampa (default: 20)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON (per uso programmatico)")
    args = parser.parse_args()

    results = []
    exit_code = 0

    for stl_arg in args.stl_files:
        stl_path = Path(stl_arg).expanduser()
        if not stl_path.exists():
            print(f"[ERRORE] File non trovato: {stl_path}", file=sys.stderr)
            exit_code = 1
            continue

        if not stl_path.suffix.lower() == ".stl":
            print(f"[WARN] Estensione non .stl: {stl_path.name}", file=sys.stderr)

        try:
            result = analyze_file(stl_path, args.infill)
        except Exception as e:
            print(f"[ERRORE] Analisi fallita per {stl_path.name}: {e}", file=sys.stderr)
            exit_code = 1
            continue

        results.append(result)

        # Segnala mesh non-manifold come warning (exit code 1 ma continua)
        m = result.get("manifold", {})
        if m and not m.get("is_manifold"):
            exit_code = max(exit_code, 1)

    if not results:
        sys.exit(exit_code)

    if args.json:
        out = results[0] if len(results) == 1 else results
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print_report(result)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
