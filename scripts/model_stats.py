#!/usr/bin/env python3
"""
PANDA 3D — Statistiche Modelli Generati
==========================================

Analizza STL e result JSON per produrre statistiche complete:
- Numero totale modelli STL
- Dimensione totale (MB)
- Tasso di successo (STL generati vs task generate_3d tentati)
- Modello più grande e più piccolo
- Tempo medio di generazione

Uso:
  python3 model_stats.py
  python3 model_stats.py --json          (output JSON raw)
  python3 model_stats.py --top 10        (top 10 modelli per dimensione)
  python3 model_stats.py --verbose       (dettaglio per ogni modello)
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PANDA_HOME  = Path.home() / "panda"
STL_DIR     = PANDA_HOME / "models" / "stl"
SCAD_DIR    = PANDA_HOME / "models" / "scad"
RESULTS_DIR = PANDA_HOME / "results"
TASKS_DONE  = PANDA_HOME / "tasks" / "done"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_size(b: int) -> str:
    if b >= 1_048_576:
        return f"{b/1_048_576:.2f} MB"
    if b >= 1024:
        return f"{b/1024:.1f} KB"
    return f"{b} B"


def fmt_duration(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    m, s = divmod(int(secs), 60)
    return f"{m}m{s:02d}s"


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_stl_info() -> list[dict]:
    """Raccoglie info su ogni STL presente."""
    if not STL_DIR.exists():
        return []

    models = []
    for stl in STL_DIR.glob("*.stl"):
        stat = stl.stat()
        scad = SCAD_DIR / (stl.stem + ".scad")
        models.append({
            "filename":     stl.name,
            "stem":         stl.stem,
            "path":         stl,
            "size_bytes":   stat.st_size,
            "size_kb":      round(stat.st_size / 1024, 2),
            "mtime":        datetime.fromtimestamp(stat.st_mtime),
            "has_scad":     scad.exists(),
            "task_id":      None,
            "description":  "",
            "gen_secs":     None,
            "quality":      None,
            "object_type":  None,
        })
    return models


def collect_results() -> tuple[list[dict], list[dict]]:
    """
    Analizza i file in results/ e ritorna:
      (generate_3d_results, all_results)
    """
    all_results = []
    gen3d = []

    if not RESULTS_DIR.exists():
        return gen3d, all_results

    for rfile in RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(rfile.read_text(encoding="utf-8"))
        except Exception:
            continue

        all_results.append(data)

        # Identifica task generate_3d: campo type oppure stl_file presente
        task_type = data.get("type", data.get("task", {}).get("type", ""))
        if task_type == "generate_3d" or "stl_file" in data:
            # Calcola durata
            started  = parse_iso(data.get("started_at"))
            finished = parse_iso(data.get("finished_at"))
            duration = None
            if started and finished:
                duration = (finished - started).total_seconds()

            gen3d.append({
                "task_id":     data.get("task_id", ""),
                "success":     data.get("success", False),
                "stl_file":    data.get("stl_file"),
                "file_size_kb": data.get("file_size_kb", 0),
                "description": data.get("description",
                               data.get("task", {}).get("description", "")),
                "quality":     data.get("quality",
                               data.get("task", {}).get("quality", "")),
                "object_type": data.get("object_type",
                               data.get("task", {}).get("object_type", "")),
                "error":       data.get("error_message", ""),
                "duration_s":  duration,
                "finished_at": finished,
                "result_file": rfile.name,
            })

    return gen3d, all_results


def match_results_to_stl(stl_list: list[dict], gen3d: list[dict]) -> list[dict]:
    """Arricchisce gli STL con i dati dai result."""
    result_by_stem = {}
    for r in gen3d:
        if r.get("stl_file"):
            stem = Path(r["stl_file"]).stem
            result_by_stem[stem] = r

    for stl in stl_list:
        r = result_by_stem.get(stl["stem"])
        if r:
            stl["task_id"]    = r["task_id"]
            stl["description"]= r["description"]
            stl["gen_secs"]   = r["duration_s"]
            stl["quality"]    = r["quality"]
            stl["object_type"]= r["object_type"]

    return stl_list


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def compute_stats(stl_list: list[dict], gen3d: list[dict]) -> dict:
    total_stl   = len(stl_list)
    total_bytes = sum(m["size_bytes"] for m in stl_list)
    total_scad  = sum(1 for m in stl_list if m["has_scad"])

    # Dimensioni estreme
    if stl_list:
        by_size = sorted(stl_list, key=lambda m: m["size_bytes"])
        smallest = by_size[0]
        largest  = by_size[-1]
    else:
        smallest = largest = None

    # Tasso successo
    attempted = len(gen3d)
    succeeded = sum(1 for r in gen3d if r["success"])
    failed    = attempted - succeeded
    success_rate = round(succeeded / attempted * 100, 1) if attempted else 0

    # Tempi generazione
    durations = [r["duration_s"] for r in gen3d if r["duration_s"] is not None]
    avg_secs  = sum(durations) / len(durations) if durations else None
    min_secs  = min(durations) if durations else None
    max_secs  = max(durations) if durations else None

    # Distribuzione per quality
    quality_dist = defaultdict(lambda: {"attempted": 0, "succeeded": 0})
    for r in gen3d:
        q = r.get("quality") or "—"
        quality_dist[q]["attempted"] += 1
        if r["success"]:
            quality_dist[q]["succeeded"] += 1

    # Distribuzione per object_type
    type_dist = defaultdict(lambda: {"attempted": 0, "succeeded": 0})
    for r in gen3d:
        ot = r.get("object_type") or "—"
        type_dist[ot]["attempted"] += 1
        if r["success"]:
            type_dist[ot]["succeeded"] += 1

    # Errori più comuni
    errors = [r["error"] for r in gen3d if not r["success"] and r.get("error")]
    error_types = defaultdict(int)
    for e in errors:
        snippet = str(e)[:80].strip()
        if snippet:
            error_types[snippet] += 1
    top_errors = sorted(error_types.items(), key=lambda x: -x[1])[:5]

    # Timeline: modelli per giorno
    day_counts = defaultdict(int)
    for m in stl_list:
        day = m["mtime"].strftime("%Y-%m-%d")
        day_counts[day] += 1

    return {
        "total_stl":      total_stl,
        "total_bytes":    total_bytes,
        "total_scad":     total_scad,
        "smallest":       smallest,
        "largest":        largest,
        "attempted":      attempted,
        "succeeded":      succeeded,
        "failed":         failed,
        "success_rate":   success_rate,
        "avg_secs":       avg_secs,
        "min_secs":       min_secs,
        "max_secs":       max_secs,
        "quality_dist":   dict(quality_dist),
        "type_dist":      dict(type_dist),
        "top_errors":     top_errors,
        "day_counts":     dict(sorted(day_counts.items())),
        "durations_count": len(durations),
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_stats(stats: dict, stl_list: list[dict], gen3d: list[dict], top_n: int = 5):
    sep = "─" * 64

    print(f"\n{'='*64}")
    print(f"  PANDA 3D — Statistiche Modelli")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*64}")

    # ── Panoramica ──────────────────────────────────────────────────────
    print(f"\n{'▶ PANORAMICA':}")
    print(f"  Modelli STL totali : {stats['total_stl']}")
    print(f"  Dimensione totale  : {fmt_size(stats['total_bytes'])}")
    print(f"  SCAD disponibili   : {stats['total_scad']}/{stats['total_stl']}")
    if stats["total_stl"] > 0:
        avg_kb = stats["total_bytes"] / 1024 / stats["total_stl"]
        print(f"  Dimensione media   : {avg_kb:.1f} KB")

    # ── Dimensioni estreme ──────────────────────────────────────────────
    if stats["smallest"] and stats["largest"]:
        print(f"\n▶ DIMENSIONI ESTREME")
        s = stats["smallest"]
        l = stats["largest"]
        print(f"  Più piccolo : {s['filename']:<38} {fmt_size(s['size_bytes']):>8}")
        print(f"  Più grande  : {l['filename']:<38} {fmt_size(l['size_bytes']):>8}")

    # ── Tasso successo ──────────────────────────────────────────────────
    if stats["attempted"] > 0:
        bar_len = 30
        filled  = round(stats["success_rate"] / 100 * bar_len)
        bar     = "█" * filled + "░" * (bar_len - filled)
        print(f"\n▶ TASSO DI SUCCESSO  (da {stats['attempted']} tentativi generate_3d)")
        print(f"  [{bar}] {stats['success_rate']}%")
        print(f"  Riusciti : {stats['succeeded']}")
        print(f"  Falliti  : {stats['failed']}")
    else:
        print(f"\n▶ TASSO DI SUCCESSO")
        print(f"  Nessun risultato generate_3d trovato nei result JSON")
        if stats["total_stl"] > 0:
            print(f"  (esistono {stats['total_stl']} STL ma senza result JSON corrispondente)")

    # ── Tempi di generazione ────────────────────────────────────────────
    if stats["avg_secs"] is not None:
        print(f"\n▶ TEMPI DI GENERAZIONE  ({stats['durations_count']} misurazioni)")
        print(f"  Medio   : {fmt_duration(stats['avg_secs'])}")
        print(f"  Minimo  : {fmt_duration(stats['min_secs'])}")
        print(f"  Massimo : {fmt_duration(stats['max_secs'])}")
    else:
        print(f"\n▶ TEMPI DI GENERAZIONE")
        print(f"  Dati non disponibili (i result non contengono started_at/finished_at)")

    # ── Distribuzione per qualità ───────────────────────────────────────
    if stats["quality_dist"]:
        print(f"\n▶ PER QUALITÀ")
        for q, d in sorted(stats["quality_dist"].items()):
            rate = round(d['succeeded']/d['attempted']*100) if d['attempted'] else 0
            print(f"  {q:<10} : {d['succeeded']}/{d['attempted']} ok  ({rate}%)")

    # ── Distribuzione per tipo oggetto ──────────────────────────────────
    if stats["type_dist"]:
        print(f"\n▶ PER TIPO OGGETTO")
        for ot, d in sorted(stats["type_dist"].items()):
            rate = round(d['succeeded']/d['attempted']*100) if d['attempted'] else 0
            print(f"  {ot:<12} : {d['succeeded']}/{d['attempted']} ok  ({rate}%)")

    # ── Top N per dimensione ─────────────────────────────────────────────
    if stl_list and top_n > 0:
        print(f"\n▶ TOP {top_n} PER DIMENSIONE")
        print(f"  {sep}")
        print(f"  {'NOME':<38} {'SIZE':>8}  DATA")
        print(f"  {sep}")
        for m in sorted(stl_list, key=lambda x: -x["size_bytes"])[:top_n]:
            mtime = m["mtime"].strftime("%Y-%m-%d")
            print(f"  {m['filename']:<38} {fmt_size(m['size_bytes']):>8}  {mtime}")

    # ── Errori comuni ────────────────────────────────────────────────────
    if stats["top_errors"]:
        print(f"\n▶ ERRORI PIÙ FREQUENTI (task falliti)")
        for err, cnt in stats["top_errors"]:
            print(f"  x{cnt}  {err}")

    # ── Timeline ─────────────────────────────────────────────────────────
    if stats["day_counts"]:
        print(f"\n▶ MODELLI PER GIORNO")
        for day, cnt in sorted(stats["day_counts"].items())[-10:]:
            bar = "▪" * cnt
            print(f"  {day}  {bar} ({cnt})")

    print(f"\n{'='*64}")


def print_verbose(stl_list: list[dict]):
    """Tabella dettagliata per ogni STL."""
    if not stl_list:
        return
    print(f"\n▶ DETTAGLIO TUTTI I MODELLI ({len(stl_list)})")
    print(f"  {'NOME':<36} {'SIZE':>8}  {'TIME':>7}  {'TIPO':<12}  DATA")
    print(f"  {'─'*76}")
    for m in sorted(stl_list, key=lambda x: x["mtime"], reverse=True):
        gen_s   = fmt_duration(m["gen_secs"]) if m["gen_secs"] else "—"
        ot      = (m["object_type"] or "—")[:11]
        mtime   = m["mtime"].strftime("%Y-%m-%d")
        scad_ic = "✓" if m["has_scad"] else " "
        print(f"  {m['filename']:<36} {fmt_size(m['size_bytes']):>8}  {gen_s:>7}  {ot:<12}  {mtime} {scad_ic}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PANDA 3D — Statistiche modelli generati",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", action="store_true", help="Output JSON grezzo")
    parser.add_argument("--top", type=int, default=5, help="Mostra top N modelli per dimensione (default: 5)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Dettaglio per ogni modello")
    args = parser.parse_args()

    # Raccolta dati
    stl_list        = collect_stl_info()
    gen3d, all_res  = collect_results()
    stl_list        = match_results_to_stl(stl_list, gen3d)
    stats           = compute_stats(stl_list, gen3d)

    # Output JSON
    if args.json:
        out = {
            **stats,
            "smallest":  {k: str(v) if isinstance(v, Path) else v
                          for k, v in (stats["smallest"] or {}).items()
                          if k != "path"},
            "largest":   {k: str(v) if isinstance(v, Path) else v
                          for k, v in (stats["largest"] or {}).items()
                          if k != "path"},
            "models":    [{k: str(v) if isinstance(v, (Path, datetime)) else v
                           for k, v in m.items() if k != "path"}
                          for m in stl_list],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return

    # Output testuale
    print_stats(stats, stl_list, gen3d, top_n=args.top)
    if args.verbose:
        print_verbose(stl_list)


if __name__ == "__main__":
    main()
