#!/usr/bin/env python3
"""
cleanup_cache.py — Pulizia file vecchi PANDA 3D
================================================
Elimina file temporanei e vecchi per liberare spazio su disco.

Regole di pulizia:
  ~/panda/cache/       → file più vecchi di 7 giorni
  ~/panda/scripts/     → temp_*.py più vecchi di 1 giorno
  ~/panda/results/     → JSON più vecchi di 30 giorni
  ~/panda/logs/        → .log più vecchi di 30 giorni

Uso:
  python3 cleanup_cache.py              # anteprima (dry-run)
  python3 cleanup_cache.py --execute    # esecuzione reale
  python3 cleanup_cache.py --json       # output JSON
  python3 cleanup_cache.py --quiet      # solo riepilogo finale
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PANDA_HOME = Path.home() / "panda"

RULES = [
    {
        "label":   "Cache SCAD",
        "dir":     PANDA_HOME / "cache",
        "pattern": "*.scad",
        "max_age_days": 7,
    },
    {
        "label":   "Script temporanei",
        "dir":     PANDA_HOME / "scripts",
        "pattern": "temp_*.py",
        "max_age_days": 1,
    },
    {
        "label":   "Risultati vecchi",
        "dir":     PANDA_HOME / "results",
        "pattern": "*.json",
        "max_age_days": 30,
    },
    {
        "label":   "Log vecchi",
        "dir":     PANDA_HOME / "logs",
        "pattern": "*.log",
        "max_age_days": 30,
    },
]

# ──────────────────────────────────────────────────────────────────────────────

def _human_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    if n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.1f} KB"
    return f"{n_bytes / 1024 ** 2:.2f} MB"


def _fmt_age(mtime: float) -> str:
    age = timedelta(seconds=time.time() - mtime)
    days = age.days
    hours = age.seconds // 3600
    if days > 0:
        return f"{days}g {hours}h"
    return f"{hours}h"


def run_cleanup(execute: bool = False, quiet: bool = False, verbose: bool = False):
    now = time.time()
    report = {
        "executed": execute,
        "timestamp": datetime.now().isoformat(),
        "rules": [],
        "totals": {"files": 0, "bytes": 0},
    }

    for rule in RULES:
        d = rule["dir"]
        max_age_s = rule["max_age_days"] * 86400
        rule_result = {
            "label":       rule["label"],
            "dir":         str(d),
            "pattern":     rule["pattern"],
            "max_age_days": rule["max_age_days"],
            "candidates":  [],
            "deleted":     0,
            "bytes_freed": 0,
            "errors":      [],
        }

        if not d.exists():
            if not quiet:
                print(f"  ⚠  {rule['label']}: directory non trovata ({d})")
            report["rules"].append(rule_result)
            continue

        candidates = list(d.glob(rule["pattern"]))
        expired = [f for f in candidates if (now - f.stat().st_mtime) > max_age_s]

        if not quiet:
            label_str = f"[{rule['label']}]"
            age_str   = f"{rule['max_age_days']}g"
            print(f"\n{label_str} {d} (pattern={rule['pattern']}, max={age_str})")
            print(f"  Totale file: {len(candidates)}  |  Scaduti: {len(expired)}")

        for f in sorted(expired, key=lambda p: p.stat().st_mtime):
            stat = f.stat()
            size = stat.st_size
            age_str = _fmt_age(stat.st_mtime)
            rule_result["candidates"].append({"name": f.name, "size": size, "age": age_str})

            if verbose and not quiet:
                print(f"    {'DEL' if execute else 'OLD'} {f.name:50s}  {_human_size(size):>8}  ({age_str})")

            if execute:
                try:
                    f.unlink()
                    rule_result["deleted"] += 1
                    rule_result["bytes_freed"] += size
                    report["totals"]["files"] += 1
                    report["totals"]["bytes"] += size
                except Exception as exc:
                    rule_result["errors"].append({"file": f.name, "error": str(exc)})
                    if not quiet:
                        print(f"    ✗ Errore eliminazione {f.name}: {exc}", file=sys.stderr)
            else:
                # dry-run: conta come se eliminato
                rule_result["bytes_freed"] += size
                report["totals"]["files"] += 1
                report["totals"]["bytes"] += size

        if not quiet:
            action = "Liberati" if execute else "Liberabili"
            print(f"  → {action}: {len(expired)} file | {_human_size(rule_result['bytes_freed'])}")

        report["rules"].append(rule_result)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Pulizia file vecchi PANDA 3D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Esegui davvero l'eliminazione (default: dry-run)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output in formato JSON",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Stampa solo il riepilogo finale",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Mostra ogni file scaduto",
    )
    args = parser.parse_args()

    if not args.json and not args.quiet:
        mode = "ESECUZIONE" if args.execute else "DRY-RUN (usa --execute per eliminare davvero)"
        print(f"━━━  PANDA 3D — Cleanup cache  ━━━  {mode}")
        print(f"Home: {PANDA_HOME}\n")

    report = run_cleanup(
        execute=args.execute,
        quiet=args.quiet or args.json,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # Riepilogo finale
    totals = report["totals"]
    action_past = "Eliminati" if args.execute else "Trovati (dry-run)"
    print(f"\n{'━'*50}")
    print(f"  {action_past}: {totals['files']} file — {_human_size(totals['bytes'])} liberati")

    if not args.execute and totals["files"] > 0:
        print("  💡 Esegui con --execute per rimuovere questi file.")

    if args.execute and totals["files"] == 0:
        print("  ✓ Nessun file da eliminare — sistema già pulito.")


if __name__ == "__main__":
    main()
