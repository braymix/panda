#!/usr/bin/env python3
"""
PANDA 3D — Batch Import Task 3D
================================

Importa task generate_3d da ~/panda/tasks/examples/ (o da un path custom)
verso la coda PANDA via API /api/tasks/import.

Formati supportati per ogni file JSON:
  - Singolo task:   { "id": "...", "type": "generate_3d", ... }
  - Batch (multi):  { "tasks": [ {...}, {...} ] }

Uso:
  python3 batch_import_3d.py
  python3 batch_import_3d.py --dir ~/panda/tasks/examples/
  python3 batch_import_3d.py --dir /altro/path --yes
  python3 batch_import_3d.py --file batch_cucina.json
  python3 batch_import_3d.py --api http://localhost:5000 --yes
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("[ERROR] Modulo 'requests' non installato. Esegui: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_DIR = Path.home() / "panda" / "tasks" / "examples"
DEFAULT_API = "http://localhost:5000"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def load_tasks_from_file(path: Path) -> list[dict]:
    """
    Legge un file JSON e restituisce una lista di task.
    Supporta sia singolo task che formato batch {"tasks": [...]}.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON non valido in {path.name}: {e}")
        return []
    except Exception as e:
        print(f"  [WARN] Errore lettura {path.name}: {e}")
        return []

    # Formato batch: {"tasks": [...]}
    if isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        tasks = data["tasks"]
        print(f"  📦 {path.name}: batch con {len(tasks)} task")
        return tasks

    # Singolo task: {"id": ..., "type": ...}
    if isinstance(data, dict) and "id" in data:
        print(f"  📄 {path.name}: singolo task '{data['id']}'")
        return [data]

    # Array diretto di task
    if isinstance(data, list):
        print(f"  📋 {path.name}: array con {len(data)} task")
        return data

    print(f"  [WARN] {path.name}: formato non riconosciuto, salto")
    return []


def load_all_tasks(source_dir: Path, single_file: Path | None = None) -> list[dict]:
    """Raccoglie tutti i task dalla directory (o da un singolo file)."""
    all_tasks = []

    if single_file:
        files = [single_file]
    else:
        files = sorted(source_dir.glob("*.json"))
        if not files:
            print(f"[ERROR] Nessun file .json trovato in: {source_dir}")
            sys.exit(1)

    print(f"\n📂 Caricamento da: {source_dir if not single_file else single_file}")
    print(f"   File trovati: {len(files)}\n")

    for f in files:
        tasks = load_tasks_from_file(f)
        all_tasks.extend(tasks)

    return all_tasks


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_TYPES = {"generate_3d", "compile_scad", "validate_scad", "bash", "python", "file", "prompt"}
VALID_QUALITY = {"fast", "medium", "high"}
VALID_OBJ_TYPE = {"simple", "mechanical", "decorative"}


def validate_task(task: dict, idx: int) -> list[str]:
    """Ritorna lista di problemi (vuota = OK)."""
    issues = []
    if "id" not in task:
        issues.append("campo 'id' mancante")
    if "type" not in task:
        issues.append("campo 'type' mancante")
    elif task["type"] not in VALID_TYPES:
        issues.append(f"type '{task['type']}' non riconosciuto (validi: {VALID_TYPES})")
    if task.get("type") == "generate_3d":
        if not task.get("description", "").strip():
            issues.append("'description' vuota per task generate_3d")
        q = task.get("quality", "medium")
        if q not in VALID_QUALITY:
            issues.append(f"quality '{q}' non valida (valide: {VALID_QUALITY})")
        ot = task.get("object_type", "simple")
        if ot not in VALID_OBJ_TYPE:
            issues.append(f"object_type '{ot}' non valido (validi: {VALID_OBJ_TYPE})")
    return issues


# ---------------------------------------------------------------------------
# Import via API
# ---------------------------------------------------------------------------

def import_tasks(tasks: list[dict], api_base: str) -> dict:
    """POST /api/tasks/import e ritorna il risultato."""
    url = f"{api_base.rstrip('/')}/api/tasks/import"
    resp = requests.post(url, json={"tasks": tasks}, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_task_table(tasks: list[dict]):
    """Stampa una tabella leggibile dei task da importare."""
    print(f"\n{'─'*72}")
    print(f"  {'#':>3}  {'ID':<26} {'TIPO':<14} {'PRIO':>4}  {'OGGETTO':<12}  QUALITÀ")
    print(f"{'─'*72}")
    for i, t in enumerate(tasks, 1):
        tid      = str(t.get("id", "?"))[:25]
        ttype    = str(t.get("type", "?"))[:13]
        prio     = str(t.get("priority", "—"))
        obj_type = str(t.get("object_type", "—"))[:11]
        quality  = str(t.get("quality", "—"))
        print(f"  {i:>3}  {tid:<26} {ttype:<14} {prio:>4}  {obj_type:<12}  {quality}")
    print(f"{'─'*72}")


def print_description_preview(tasks: list[dict]):
    """Stampa preview delle descrizioni."""
    print("\n📝 Descrizioni:")
    for t in tasks:
        tid  = t.get("id", "?")
        desc = t.get("description", t.get("prompt", "—"))
        preview = (desc[:90] + "…") if len(desc) > 90 else desc
        print(f"   [{tid}] {preview}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PANDA 3D — Importa task 3D batch via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dir", type=Path, default=DEFAULT_DIR,
        help=f"Directory sorgente (default: {DEFAULT_DIR})",
    )
    parser.add_argument(
        "--file", type=Path, default=None,
        help="Importa un singolo file JSON invece dell'intera directory",
    )
    parser.add_argument(
        "--api", default=DEFAULT_API,
        help=f"URL base API PANDA (default: {DEFAULT_API})",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Salta la conferma interattiva e procedi subito",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra i task senza importarli effettivamente",
    )
    parser.add_argument(
        "--priority-filter", type=int, default=None,
        help="Importa solo task con priorità <= N",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  PANDA 3D — Batch Import Task")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    # Verifica sorgente
    if args.file:
        if not args.file.exists():
            print(f"[ERROR] File non trovato: {args.file}")
            sys.exit(1)
        src_dir = args.file.parent
    else:
        src_dir = args.dir
        if not src_dir.exists():
            print(f"[ERROR] Directory non trovata: {src_dir}")
            print(f"  Crea con: mkdir -p {src_dir}")
            sys.exit(1)

    # Verifica API raggiungibile
    print(f"\n🔌 Verifica API: {args.api} ...")
    try:
        r = requests.get(f"{args.api.rstrip('/')}/api/status", timeout=8)
        r.raise_for_status()
        status = r.json()
        panda_state = "Attivo ✓" if status.get("panda_running") else "Fermo (worker non attivo)"
        print(f"   Dashboard OK — PANDA: {panda_state}")
    except requests.exceptions.ConnectionError:
        print(f"   [ERROR] Dashboard non raggiungibile su {args.api}")
        print(f"   Avvia con: cd ~/panda/dashboard && python3 server.py")
        sys.exit(1)
    except Exception as e:
        print(f"   [WARN] Status check fallito: {e} — continuo comunque")

    # Carica task
    all_tasks = load_all_tasks(src_dir, single_file=args.file)

    if not all_tasks:
        print("\n[ERROR] Nessun task trovato da importare.")
        sys.exit(1)

    # Validazione
    print(f"\n🔍 Validazione {len(all_tasks)} task...")
    valid_tasks = []
    has_errors = False
    for i, t in enumerate(all_tasks):
        issues = validate_task(t, i)
        if issues:
            print(f"   ⚠ Task #{i+1} '{t.get('id','?')}': {'; '.join(issues)}")
            has_errors = True
        else:
            valid_tasks.append(t)

    if has_errors and not args.yes:
        print(f"\n   {len(valid_tasks)}/{len(all_tasks)} task validi.")

    all_tasks = valid_tasks
    if not all_tasks:
        print("[ERROR] Nessun task valido da importare.")
        sys.exit(1)

    # Filtro priorità
    if args.priority_filter is not None:
        before = len(all_tasks)
        all_tasks = [t for t in all_tasks if int(t.get("priority", 10)) <= args.priority_filter]
        print(f"\n🎯 Filtro priorità <= {args.priority_filter}: {before} → {len(all_tasks)} task")

    # Ordina per priorità
    all_tasks.sort(key=lambda t: int(t.get("priority", 10)))

    # Mostra tabella
    print_task_table(all_tasks)
    print_description_preview(all_tasks)
    print(f"\n   Totale: {len(all_tasks)} task  |  API: {args.api}")

    if args.dry_run:
        print("\n[DRY RUN] Nessun task importato. Rimuovi --dry-run per procedere.")
        sys.exit(0)

    # Conferma
    if not args.yes:
        print()
        try:
            answer = input("Importare questi task nella coda PANDA? [s/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAnnullato.")
            sys.exit(0)
        if answer not in ("s", "si", "sì", "y", "yes"):
            print("Annullato.")
            sys.exit(0)

    # Import
    print(f"\n📤 Importazione in corso...")
    try:
        result = import_tasks(all_tasks, args.api)
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Connessione persa durante import.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] API ha risposto con errore: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Errore import: {e}")
        sys.exit(1)

    # Risultato
    imported = result.get("imported", 0)
    filenames = result.get("filenames", [])
    print(f"\n{'='*72}")
    print(f"  ✅ Importati {imported} task nella coda PANDA!")
    if filenames:
        print(f"\n  File creati in ~/panda/tasks/:")
        for fn in filenames:
            print(f"    • {fn}")
    print(f"\n  Monitora l'avanzamento su: {args.api}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
