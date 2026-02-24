#!/usr/bin/env python3
"""
PANDA 3D — Export Modelli in ZIP
==================================

Crea un archivio ZIP con tutti gli STL (e opzionalmente i file SCAD associati)
presenti in ~/panda/models/.

Uso:
  python3 export_models.py
  python3 export_models.py --output ~/Desktop/panda_export.zip
  python3 export_models.py --include-scad
  python3 export_models.py --filter test_    (solo STL che iniziano con "test_")
  python3 export_models.py --since 2026-02-01
"""

import argparse
import json
import sys
import zipfile
from datetime import datetime, date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PANDA_HOME  = Path.home() / "panda"
STL_DIR     = PANDA_HOME / "models" / "stl"
SCAD_DIR    = PANDA_HOME / "models" / "scad"
RESULTS_DIR = PANDA_HOME / "results"
EXPORT_DIR  = PANDA_HOME / "models"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_size(bytes_: int) -> str:
    if bytes_ >= 1_048_576:
        return f"{bytes_ / 1_048_576:.2f} MB"
    if bytes_ >= 1024:
        return f"{bytes_ / 1024:.1f} KB"
    return f"{bytes_} B"


def find_scad_for_stl(stl_path: Path) -> Path | None:
    """Cerca il file SCAD corrispondente allo STL (stesso stem)."""
    candidate = SCAD_DIR / (stl_path.stem + ".scad")
    return candidate if candidate.exists() else None


def get_result_meta(stl_name: str) -> dict:
    """Cerca nei results/ il task_id e la descrizione associati a questo STL."""
    stem = Path(stl_name).stem
    for rfile in RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(rfile.read_text(encoding="utf-8"))
            stl = data.get("stl_file", "")
            if stl and Path(stl).stem == stem:
                return {
                    "task_id":     data.get("task_id", ""),
                    "description": data.get("description", ""),
                    "generated":   data.get("finished_at", ""),
                }
        except Exception:
            continue
    return {}


def write_manifest(stl_files: list[Path], include_scad: bool) -> str:
    """Genera il contenuto del file manifest.json da includere nello zip."""
    entries = []
    for stl in stl_files:
        stat = stl.stat()
        meta = get_result_meta(stl.name)
        entry = {
            "filename":    stl.name,
            "size_kb":     round(stat.st_size / 1024, 2),
            "modified":    datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "task_id":     meta.get("task_id", ""),
            "description": meta.get("description", ""),
            "generated":   meta.get("generated", ""),
            "scad_included": False,
        }
        if include_scad:
            scad = find_scad_for_stl(stl)
            entry["scad_included"] = scad is not None
            if scad:
                entry["scad_filename"] = scad.name
        entries.append(entry)

    manifest = {
        "exported_at":   datetime.now().isoformat(),
        "total_models":  len(entries),
        "total_size_kb": round(sum(e["size_kb"] for e in entries), 2),
        "scad_included": include_scad,
        "models":        entries,
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PANDA 3D — Esporta modelli STL in archivio ZIP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Percorso output ZIP (default: ~/panda/models/export_{timestamp}.zip)",
    )
    parser.add_argument(
        "--include-scad", action="store_true",
        help="Includi anche i file .scad corrispondenti",
    )
    parser.add_argument(
        "--filter", default=None, metavar="PREFIX",
        help="Includi solo STL il cui nome contiene questa stringa",
    )
    parser.add_argument(
        "--since", default=None, metavar="YYYY-MM-DD",
        help="Includi solo STL creati dopo questa data",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="Elenca i modelli disponibili senza creare lo zip",
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  PANDA 3D — Export Modelli ZIP")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 64)

    # Verifica directory STL
    if not STL_DIR.exists() or not list(STL_DIR.glob("*.stl")):
        print(f"\n[INFO] Nessun file STL trovato in: {STL_DIR}")
        print("  Genera prima qualche modello con PANDA 3D!")
        sys.exit(0)

    # Raccogli STL
    stl_files = sorted(STL_DIR.glob("*.stl"), key=lambda p: p.stat().st_mtime)

    # Filtro per stringa
    if args.filter:
        stl_files = [f for f in stl_files if args.filter in f.name]
        print(f"\n🔍 Filtro '{args.filter}': {len(stl_files)} file corrispondenti")

    # Filtro per data
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            print(f"[ERROR] Formato data non valido: '{args.since}' (atteso: YYYY-MM-DD)")
            sys.exit(1)
        stl_files = [
            f for f in stl_files
            if datetime.fromtimestamp(f.stat().st_mtime) >= since_dt
        ]
        print(f"\n📅 Filtro --since {args.since}: {len(stl_files)} file")

    if not stl_files:
        print("\n[INFO] Nessun file STL corrisponde ai filtri applicati.")
        sys.exit(0)

    # Calcola totale
    total_bytes = sum(f.stat().st_size for f in stl_files)
    scad_files  = [find_scad_for_stl(f) for f in stl_files] if args.include_scad else []
    scad_found  = [s for s in scad_files if s is not None]
    scad_bytes  = sum(s.stat().st_size for s in scad_found)

    # Tabella modelli
    print(f"\n{'─'*64}")
    print(f"  {'NOME FILE':<40} {'DIMENSIONE':>10}  DATA")
    print(f"{'─'*64}")
    for stl in stl_files:
        stat = stl.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
        print(f"  {stl.name:<40} {format_size(stat.st_size):>10}  {mtime}")
    print(f"{'─'*64}")
    print(f"  Totale: {len(stl_files)} STL  |  {format_size(total_bytes)}", end="")
    if args.include_scad and scad_found:
        print(f"  +  {len(scad_found)} SCAD  ({format_size(scad_bytes)})", end="")
    print()

    if args.list:
        print("\n[--list] Elencazione completata. Nessuno ZIP creato.")
        sys.exit(0)

    # Output path
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.output or (EXPORT_DIR / f"export_{ts}.zip")
    out_path = Path(out_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Crea ZIP
    print(f"\n📦 Creazione archivio: {out_path} ...")
    files_added = 0
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # STL files
        for stl in stl_files:
            zf.write(stl, arcname=f"stl/{stl.name}")
            files_added += 1

        # SCAD files (opzionale)
        if args.include_scad:
            for scad in scad_found:
                zf.write(scad, arcname=f"scad/{scad.name}")
                files_added += 1

        # Manifest JSON
        manifest_str = write_manifest(stl_files, include_scad=args.include_scad)
        zf.writestr("manifest.json", manifest_str)

    zip_size = out_path.stat().st_size
    ratio = round((1 - zip_size / max(total_bytes + scad_bytes, 1)) * 100, 1)

    print(f"\n{'='*64}")
    print(f"  ✅ Export completato!")
    print(f"     File: {out_path}")
    print(f"     Contenuto: {files_added} file  ({format_size(zip_size)} compresso, -{ratio}%)")
    print(f"     Manifest: manifest.json incluso")
    print(f"{'='*64}")


if __name__ == "__main__":
    main()
