#!/usr/bin/env python3
"""
PANDA 3D — Diagnostica di Sistema
====================================

Verifica tutte le dipendenze e lo stato del sistema PANDA 3D.
Output colorato: verde=OK, giallo=WARN, rosso=FAIL.

Uso:
  python3 check_system.py
  python3 check_system.py --json        output JSON per automazione
  python3 check_system.py --fix         tenta fix automatici (crea cartelle, ecc.)
  python3 check_system.py --quiet       solo errori e warning
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------

PANDA_HOME    = Path.home() / "panda"
CONFIG_FILE   = PANDA_HOME / "config" / "panda.json"
RESULTS_DIR   = PANDA_HOME / "results"
TASKS_DIR     = PANDA_HOME / "tasks"
LOGS_DIR      = PANDA_HOME / "logs"
MODELS_STL    = PANDA_HOME / "models" / "stl"
MODELS_SCAD   = PANDA_HOME / "models" / "scad"
STATUS_FILE   = PANDA_HOME / "status" / "current.json"

REQUIRED_DIRS = [
    PANDA_HOME / "tasks",
    PANDA_HOME / "tasks" / "done",
    PANDA_HOME / "results",
    PANDA_HOME / "models" / "stl",
    PANDA_HOME / "models" / "scad",
    PANDA_HOME / "logs",
    PANDA_HOME / "config",
    PANDA_HOME / "status",
    PANDA_HOME / "prompts",
]

REQUIRED_FILES = [
    PANDA_HOME / "worker.py",
    PANDA_HOME / "dashboard" / "server.py",
    CONFIG_FILE,
]

def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {
            "ollama_url":     "http://localhost:11434",
            "model":          "qwen2.5-coder:14b-instruct-q4_K_M",
            "model_fallback": "qwen2.5-coder:7b-instruct-q8_0",
            "openscad_binary": "openscad",
        }

# ---------------------------------------------------------------------------
# Color output
# ---------------------------------------------------------------------------

USE_COLOR = sys.stdout.isatty()

def c(text: str, color: str) -> str:
    if not USE_COLOR:
        return text
    codes = {
        "green":  "\033[0;32m",
        "red":    "\033[0;31m",
        "yellow": "\033[1;33m",
        "cyan":   "\033[0;36m",
        "bold":   "\033[1m",
        "reset":  "\033[0m",
    }
    return f"{codes.get(color,'')}{text}{codes['reset']}"

def status_line(label: str, status: str, detail: str = "", fix: str = "", quiet: bool = False):
    icons = {"OK": c("✓", "green"), "WARN": c("⚠", "yellow"), "FAIL": c("✗", "red"), "INFO": c("→", "cyan")}
    icon  = icons.get(status, "?")
    color = {"OK": "green", "WARN": "yellow", "FAIL": "red", "INFO": "cyan"}.get(status, "reset")
    line  = f"  {icon}  {c(label, color)}"
    if detail:
        line += f"  —  {detail}"
    if not quiet or status in ("FAIL", "WARN"):
        print(line)
    if fix and status in ("FAIL", "WARN") and not quiet:
        print(f"       {c('Fix:', 'cyan')} {fix}")

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

class CheckResult:
    def __init__(self, name: str, status: str, detail: str = "", fix: str = ""):
        self.name   = name
        self.status = status   # OK / WARN / FAIL / INFO
        self.detail = detail
        self.fix    = fix

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail, "fix": self.fix}


def check_requests_lib() -> CheckResult:
    if HAS_REQUESTS:
        return CheckResult("requests (lib)", "OK", "modulo Python disponibile")
    return CheckResult("requests (lib)", "FAIL",
                       "modulo non installato",
                       "pip install requests")


def check_ollama(cfg: dict) -> list[CheckResult]:
    results = []
    url = cfg.get("ollama_url", "http://localhost:11434")

    if not HAS_REQUESTS:
        results.append(CheckResult("Ollama", "WARN", "skip (requests mancante)"))
        return results

    try:
        r = requests.get(f"{url}/api/tags", timeout=6)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        model_names = [m.get("name", "") for m in models]
        results.append(CheckResult("Ollama server", "OK", f"raggiungibile su {url}"))
    except requests.exceptions.ConnectionError:
        results.append(CheckResult("Ollama server", "FAIL",
                                   f"non raggiungibile su {url}",
                                   "ollama serve  oppure  sudo systemctl start ollama"))
        return results
    except Exception as e:
        results.append(CheckResult("Ollama server", "FAIL", str(e)[:80],
                                   "controlla ollama serve"))
        return results

    # Modello principale
    main_model = cfg.get("model", "")
    main_stem  = main_model.split(":")[0] if main_model else ""
    found_main = any(main_stem in n for n in model_names) if main_stem else False

    if found_main:
        # Trova il nome esatto per mostrare la versione
        matched = next(n for n in model_names if main_stem in n)
        results.append(CheckResult("LLM principale", "OK",
                                   f"{matched}  (richiesto: {main_model})"))
    else:
        results.append(CheckResult("LLM principale", "WARN",
                                   f"'{main_model}' non trovato",
                                   f"ollama pull {main_model}"))

    # Modello fallback
    fallback = cfg.get("model_fallback", "")
    fb_stem  = fallback.split(":")[0] if fallback else ""
    found_fb = any(fb_stem in n for n in model_names) if fb_stem else False

    if found_main or found_fb:
        if found_fb:
            matched_fb = next(n for n in model_names if fb_stem in n)
            results.append(CheckResult("LLM fallback", "OK", matched_fb))
        else:
            results.append(CheckResult("LLM fallback", "WARN",
                                       f"'{fallback}' non trovato (opzionale)",
                                       f"ollama pull {fallback}"))
    else:
        results.append(CheckResult("LLM fallback", "FAIL",
                                   f"'{fallback}' non trovato — nessun modello disponibile!",
                                   f"ollama pull {fallback}"))

    # Modelli installati totali
    results.append(CheckResult("Modelli Ollama", "INFO",
                               f"{len(model_names)} modell{'o' if len(model_names)==1 else 'i'} installati: "
                               + ", ".join(model_names[:4]) + ("…" if len(model_names) > 4 else "")))
    return results


def check_openscad(cfg: dict) -> CheckResult:
    binary = cfg.get("openscad_binary", "openscad")

    # Prova il binario dalla config
    path = shutil.which(binary)

    # Cerca in path alternativi se non trovato
    if not path:
        for alt in ["openscad-nightly", "/usr/bin/openscad", "/usr/local/bin/openscad",
                    "/snap/bin/openscad", "/opt/openscad/bin/openscad"]:
            if shutil.which(alt) or Path(alt).exists():
                path = alt
                break

    if not path:
        return CheckResult("OpenSCAD", "FAIL",
                           "non trovato nel PATH",
                           "sudo apt install openscad  oppure  sudo snap install openscad")

    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
        ver = (r.stdout + r.stderr).strip().split("\n")[0]
        return CheckResult("OpenSCAD", "OK", f"{path}  —  {ver}")
    except subprocess.TimeoutExpired:
        return CheckResult("OpenSCAD", "WARN", f"trovato ma --version timeout: {path}")
    except Exception as e:
        return CheckResult("OpenSCAD", "WARN", f"trovato ma errore versione: {e}")


def check_directories(fix: bool) -> list[CheckResult]:
    results = []
    for d in REQUIRED_DIRS:
        d_exp = Path(str(d).replace("~", str(Path.home())))
        if d_exp.exists():
            results.append(CheckResult(f"Dir {d_exp.relative_to(Path.home())}", "OK"))
        elif fix:
            try:
                d_exp.mkdir(parents=True, exist_ok=True)
                results.append(CheckResult(f"Dir {d_exp.relative_to(Path.home())}", "OK",
                                           "creata"))
            except Exception as e:
                results.append(CheckResult(f"Dir {d_exp.relative_to(Path.home())}", "FAIL",
                                           f"impossibile creare: {e}"))
        else:
            results.append(CheckResult(f"Dir {d_exp.relative_to(Path.home())}", "FAIL",
                                       "mancante",
                                       f"mkdir -p {d_exp}"))
    return results


def check_files() -> list[CheckResult]:
    results = []
    for f in REQUIRED_FILES:
        f_exp = Path(str(f).replace("~", str(Path.home())))
        if f_exp.exists():
            size = f_exp.stat().st_size
            results.append(CheckResult(f"File {f_exp.name}", "OK",
                                       f"{f_exp}  ({size//1024} KB)" if size > 1024 else str(f_exp)))
        else:
            results.append(CheckResult(f"File {f_exp.name}", "FAIL",
                                       f"non trovato: {f_exp}"))
    return results


def check_disk_space() -> CheckResult:
    target = MODELS_STL if MODELS_STL.exists() else PANDA_HOME
    try:
        usage = shutil.disk_usage(target)
        free_gb  = usage.free  / 1_073_741_824
        total_gb = usage.total / 1_073_741_824
        used_pct = round((usage.used / usage.total) * 100, 1)
        detail   = f"{free_gb:.1f} GB liberi / {total_gb:.1f} GB totali  ({used_pct}% usato)"
        if free_gb < 1.0:
            return CheckResult("Spazio disco", "FAIL", detail,
                               "libera spazio — i modelli 3D richiedono almeno 1 GB")
        elif free_gb < 5.0:
            return CheckResult("Spazio disco", "WARN", detail)
        return CheckResult("Spazio disco", "OK", detail)
    except Exception as e:
        return CheckResult("Spazio disco", "WARN", f"impossibile verificare: {e}")


def check_systemd_service(name: str) -> CheckResult:
    """Verifica stato servizio systemd (graceful se systemd non disponibile)."""
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5
        )
        state = r.stdout.strip()
        if state == "active":
            return CheckResult(f"systemd {name}", "OK", "running")
        elif state == "inactive":
            return CheckResult(f"systemd {name}", "WARN", "stopped",
                               f"sudo systemctl start {name}")
        elif state == "failed":
            return CheckResult(f"systemd {name}", "FAIL", "failed",
                               f"sudo journalctl -u {name} -n 20")
        else:
            return CheckResult(f"systemd {name}", "WARN", f"stato: {state}")
    except FileNotFoundError:
        return CheckResult(f"systemd {name}", "INFO", "systemd non disponibile in questo ambiente")
    except subprocess.TimeoutExpired:
        return CheckResult(f"systemd {name}", "WARN", "timeout verifica stato")
    except Exception as e:
        return CheckResult(f"systemd {name}", "INFO", f"non verificabile: {e}")


def check_last_task() -> CheckResult:
    """Trova l'ultimo task generate_3d eseguito e il suo esito."""
    if not RESULTS_DIR.exists():
        return CheckResult("Ultimo task", "INFO", "nessun result trovato")

    result_files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not result_files:
        return CheckResult("Ultimo task", "INFO", "nessun result trovato")

    # Cerca l'ultimo generate_3d
    for rfile in result_files[:30]:
        try:
            data = json.loads(rfile.read_text())
        except Exception:
            continue

        task_type = data.get("type", data.get("task", {}).get("type", ""))
        if task_type != "generate_3d" and "stl_file" not in data:
            continue

        task_id  = data.get("task_id", rfile.stem)
        success  = data.get("success", False)
        finished = data.get("finished_at", "")
        stl      = data.get("stl_file", "")
        desc     = data.get("description", "")[:50]

        if finished:
            try:
                fin_dt = datetime.fromisoformat(finished[:19])
                delta  = datetime.now() - fin_dt
                ago    = _humanize_delta(delta)
            except Exception:
                ago = finished[:16]
        else:
            ago = "?"

        detail = f"[{task_id}] {ago}"
        if desc:
            detail += f"  —  {desc[:40]}…" if len(desc) >= 40 else f"  —  {desc}"
        if stl:
            detail += f"  →  {Path(stl).name}"

        if success:
            return CheckResult("Ultimo task 3D", "OK", detail)
        else:
            err = data.get("error_message", data.get("error", ""))[:60]
            return CheckResult("Ultimo task 3D", "WARN",
                               detail + (f"\n       Errore: {err}" if err else ""))

    # Nessun generate_3d, mostra l'ultimo qualsiasi
    try:
        data = json.loads(result_files[0].read_text())
        tid  = data.get("task_id", result_files[0].stem)
        suc  = "✓" if data.get("success") else "✗"
        return CheckResult("Ultimo task (gen.)", "INFO",
                           f"nessun generate_3d recente — ultimo: [{tid}] {suc}")
    except Exception:
        return CheckResult("Ultimo task", "INFO", "nessun generate_3d recente")


def check_stl_count() -> CheckResult:
    if not MODELS_STL.exists():
        return CheckResult("Modelli STL", "INFO", "directory non esiste ancora")
    stls = list(MODELS_STL.glob("*.stl"))
    if not stls:
        return CheckResult("Modelli STL", "INFO", "nessun modello generato ancora")
    total_kb = sum(f.stat().st_size for f in stls) / 1024
    size_str = f"{total_kb/1024:.1f} MB" if total_kb > 1024 else f"{total_kb:.0f} KB"
    return CheckResult("Modelli STL", "OK", f"{len(stls)} file  —  {size_str} totali")


def check_worker_running() -> CheckResult:
    """Controlla se worker.py è in esecuzione come processo."""
    try:
        r = subprocess.run(["pgrep", "-f", "worker.py"], capture_output=True, text=True)
        pids = r.stdout.strip().split()
        if pids:
            return CheckResult("Worker processo", "OK", f"PID(s): {', '.join(pids)}")
        else:
            return CheckResult("Worker processo", "WARN", "worker.py non in esecuzione",
                               "Avvia: python3 ~/panda/worker.py  oppure  sudo systemctl start panda")
    except Exception:
        return CheckResult("Worker processo", "INFO", "non verificabile (pgrep non disponibile)")


def _humanize_delta(d: timedelta) -> str:
    secs = int(d.total_seconds())
    if secs < 60:
        return f"{secs}s fa"
    if secs < 3600:
        return f"{secs//60}m fa"
    if secs < 86400:
        return f"{secs//3600}h fa"
    return f"{secs//86400}g fa"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PANDA 3D — Diagnostica di sistema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json",  action="store_true", help="Output JSON")
    parser.add_argument("--fix",   action="store_true", help="Tenta fix automatici (crea cartelle)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Mostra solo errori e warning")
    args = parser.parse_args()

    cfg = load_config()

    all_checks: list[CheckResult] = []
    sections: list[tuple[str, list[CheckResult]]] = []

    # Raccoglie tutti i check
    sec_lib = [check_requests_lib()]
    sec_ollama = check_ollama(cfg)
    sec_openscad = [check_openscad(cfg)]
    sec_dirs = check_directories(fix=args.fix)
    sec_files = check_files()
    sec_disk = [check_disk_space()]
    sec_services = [
        check_systemd_service("panda"),
        check_systemd_service("panda-dashboard"),
        check_worker_running(),
    ]
    sec_last = [check_last_task(), check_stl_count()]

    sections = [
        ("Dipendenze Python",    sec_lib),
        ("Ollama & Modelli LLM", sec_ollama),
        ("OpenSCAD",             sec_openscad),
        ("Cartelle Progetto",    sec_dirs),
        ("File Progetto",        sec_files),
        ("Spazio Disco",         sec_disk),
        ("Servizi",              sec_services),
        ("Stato Operativo",      sec_last),
    ]
    for _, checks in sections:
        all_checks.extend(checks)

    # ── Output JSON ────────────────────────────────────────────────────────
    if args.json:
        summary = {
            "ok":   sum(1 for c in all_checks if c.status == "OK"),
            "warn": sum(1 for c in all_checks if c.status == "WARN"),
            "fail": sum(1 for c in all_checks if c.status == "FAIL"),
        }
        print(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "checks": [c.to_dict() for c in all_checks],
        }, indent=2, ensure_ascii=False))
        sys.exit(0 if summary["fail"] == 0 else 1)

    # ── Output colorato ────────────────────────────────────────────────────
    print(f"\n{c('═'*60, 'bold')}")
    print(f"{c('  PANDA 3D — Diagnostica di Sistema', 'bold')}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{c('═'*60, 'bold')}")

    for section_name, checks in sections:
        if args.quiet:
            has_issues = any(c.status in ("FAIL", "WARN") for c in checks)
            if not has_issues:
                continue
        print(f"\n{c(f'▶ {section_name}', 'bold')}")
        for chk in checks:
            status_line(chk.name, chk.status, chk.detail, chk.fix, quiet=args.quiet)

    # ── Sommario finale ────────────────────────────────────────────────────
    n_ok   = sum(1 for ch in all_checks if ch.status == "OK")
    n_warn = sum(1 for ch in all_checks if ch.status == "WARN")
    n_fail = sum(1 for ch in all_checks if ch.status == "FAIL")

    print(f"\n{c('─'*60, 'bold')}")
    print(f"  Sommario: "
          f"{c(f'{n_ok} OK', 'green')}  "
          f"{c(f'{n_warn} WARN', 'yellow')}  "
          f"{c(f'{n_fail} FAIL', 'red')}")

    if n_fail > 0:
        print(f"\n  {c('Sistema NON pronto — risolvi i FAIL prima di avviare', 'red')}")
        fails = [ch for ch in all_checks if ch.status == "FAIL"]
        for f in fails:
            if f.fix:
                print(f"  {c('→', 'cyan')} {f.name}: {f.fix}")
    elif n_warn > 0:
        print(f"\n  {c('Sistema parzialmente pronto — controlla i WARN', 'yellow')}")
    else:
        print(f"\n  {c('Sistema OK — PANDA 3D pronto!', 'green')}")
        print(f"  {c('→', 'cyan')} Avvia con: bash ~/panda/scripts/start_panda3d.sh")

    print(f"{c('─'*60, 'bold')}\n")
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
