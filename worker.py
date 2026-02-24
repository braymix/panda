#!/usr/bin/env python3
"""
PANDA 3D Worker
Pana Automating Never Death (on) Afterwork — 3D Model Generator

Features:
- Generazione modelli 3D via Ollama + OpenSCAD
- Task types 3D: generate_3d, compile_scad, validate_scad, list_models
- Task types legacy: bash, python, file, test, prompt
- Retry automatico
- Pipeline stop su gate fallito
- Stato live per dashboard
- Long-running safe
"""

import json
import re
import sys
import threading
import time
import subprocess
from datetime import datetime
from pathlib import Path

import requests

# =========================
# PATHS
# =========================

PANDA_HOME = Path.home() / "panda"
TASKS_DIR = PANDA_HOME / "tasks"
RESULTS_DIR = PANDA_HOME / "results"
LOGS_DIR = PANDA_HOME / "logs"
STATUS_DIR = PANDA_HOME / "status"
CONFIG_FILE = PANDA_HOME / "config" / "panda.json"
CURRENT_STATUS_FILE = STATUS_DIR / "current.json"
PROMPTS_DIR = PANDA_HOME / "prompts"
MODELS_SCAD_DIR = PANDA_HOME / "models" / "scad"
MODELS_STL_DIR = PANDA_HOME / "models" / "stl"

# =========================
# CONFIG
# =========================

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434",
    "model": "qwen2.5-coder:14b-instruct-q4_K_M",
    "model_fallback": "qwen2.5-coder:7b-instruct-q8_0",
    "check_interval": 15,
    "max_retries": 2,
    "openscad_binary": "openscad",
    "openscad_timeout": 300,
    "stl_format": "asciistl",
    "default_quality": "medium",
    "quality_presets": {
        "fast":   {"fn": 32,  "detail_level": "low"},
        "medium": {"fn": 64,  "detail_level": "medium"},
        "high":   {"fn": 128, "detail_level": "high"},
    },
    "default_dimensions": {"max_x": 200, "max_y": 200, "max_z": 200},
    "execute_bash": True,
    "execute_code": True,
    "modify_files": True,
    "stop_on_test_fail": False,
}

# =========================
# UTILS
# =========================

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log", "a") as f:
        f.write(line + "\n")


def _count_stl_models():
    if MODELS_STL_DIR.exists():
        return len(list(MODELS_STL_DIR.glob("*.stl")))
    return 0


def _last_stl_model():
    if not MODELS_STL_DIR.exists():
        return None
    stl_files = sorted(
        MODELS_STL_DIR.glob("*.stl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return stl_files[0].name if stl_files else None


def update_status(task_id=None, task_type=None, status="idle", progress=None):
    STATUS_DIR.mkdir(exist_ok=True)
    payload = {
        "current_task": task_id,
        "task_type": task_type,
        "status": status,
        "progress": progress,
        "updated_at": datetime.now().isoformat(),
        "last_model": _last_stl_model(),
        "models_count": _count_stl_models(),
    }
    with open(CURRENT_STATUS_FILE, "w") as f:
        json.dump(payload, f)


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def save_default_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)

# =========================
# OLLAMA
# =========================

def ask_ollama(prompt, config, system_prompt=None):
    start_time = time.time()
    stop_event = threading.Event()

    def progress_logger():
        while not stop_event.wait(30):
            elapsed = time.time() - start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            log(f"⏳ Ollama sta elaborando... ({mins}min {secs}s)")

    progress_thread = threading.Thread(target=progress_logger, daemon=True)
    progress_thread.start()

    try:
        if system_prompt:
            r = requests.post(
                f"{config['ollama_url']}/api/chat",
                json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=3600,
            )
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")
        else:
            r = requests.post(
                f"{config['ollama_url']}/api/generate",
                json={"model": config["model"], "prompt": prompt, "stream": False},
                timeout=3600,
            )
            r.raise_for_status()
            return r.json().get("response", "")
    except Exception as e:
        log(f"Ollama error: {e}", "ERROR")
        return None
    finally:
        stop_event.set()
        progress_thread.join(timeout=1)


def clean_llm(code):
    """
    Pulisce la risposta LLM rimuovendo:
    - Prefazioni (es: "Ecco il codice:", "Here is the code:", etc.)
    - Blocchi markdown ```language ... ```
    - Prima riga se è solo il nome del linguaggio
    """
    if not code:
        return ""

    code = code.strip()

    # Pattern di prefazioni comuni da rimuovere (italiano e inglese)
    preface_patterns = [
        # Italiano
        r"^[Ee]cco\s+(il|lo|la|i|gli|le|qui|qua)?\s*[^:]*[:\.]?\s*\n?",
        r"^[Cc]ertamente[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Ss]icuramente[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Dd]i seguito[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Qq]ui (c'è|ci sono|trovi)[^:]*[:\.]?\s*\n?",
        r"^[Ii]l (codice|comando|contenuto|file)[^:]*[:\.]?\s*\n?",
        r"^[Cc]ome richiesto[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Vv]olentieri[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Pp]erfetto[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Oo]k[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Bb]ene[,\.]?\s*[^:]*[:\.]?\s*\n?",
        # Inglese
        r"^[Hh]ere['\u2019]?s?\s+(is|are)?\s*[^:]*[:\.]?\s*\n?",
        r"^[Ss]ure[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Cc]ertainly[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Oo]f course[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Tt]he (code|command|content|file)[^:]*[:\.]?\s*\n?",
        r"^[Bb]elow[^:]*[:\.]?\s*\n?",
        r"^[Aa]s requested[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Ll]et me[^:]*[:\.]?\s*\n?",
        r"^[Ii]\s*(will|'ll|can|'d)\s*[^:]*[:\.]?\s*\n?",
        r"^[Hh]appy to[^:]*[:\.]?\s*\n?",
        r"^[Aa]bsolutely[,\.]?\s*[^:]*[:\.]?\s*\n?",
    ]

    for pattern in preface_patterns:
        code = re.sub(pattern, "", code, count=1)
    code = code.strip()

    # Rimuovi blocchi markdown ``` con qualsiasi linguaggio
    md_match = re.match(r"^```[\w\-]*\s*\n?([\s\S]*?)```\s*$", code, re.DOTALL)
    if md_match:
        code = md_match.group(1).strip()
    elif code.startswith("```"):
        # Fallback: split su ```
        parts = code.split("```")
        if len(parts) >= 2:
            # Prendi il contenuto tra i primi due ```
            content = parts[1]
            # Rimuovi eventuale nome linguaggio dalla prima riga
            lines = content.split("\n", 1)
            if len(lines) > 1 and lines[0].strip().lower() in [
                "python", "py", "bash", "sh", "shell", "html", "css",
                "javascript", "js", "json", "yaml", "yml", "xml", "sql",
                "dockerfile", "makefile", "markdown", "md", "txt", "text"
            ]:
                code = lines[1].strip()
            else:
                code = content.strip()

    # Rimuovi prima riga se è solo il nome del linguaggio
    lines = code.split("\n", 1)
    if lines and lines[0].strip().lower() in [
        "python", "py", "python3", "bash", "sh", "shell", "zsh",
        "html", "html5", "css", "css3", "javascript", "js", "typescript", "ts",
        "json", "yaml", "yml", "xml", "sql", "dockerfile", "makefile"
    ]:
        code = lines[1].strip() if len(lines) > 1 else ""

    return code.strip()

# =========================
# EXECUTION HELPERS
# =========================

def exec_bash(cmd):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return {"success": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def exec_python(code):
    temp = PANDA_HOME / "scripts" / f"temp_{int(time.time())}.py"
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(code)
    try:
        p = subprocess.run(
            [sys.executable, str(temp)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PANDA_HOME)
        )
        return {"success": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path, content):
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# =========================
# 3D TASK HANDLERS
# =========================

def _load_prompt_file(name):
    """Carica un file di prompt, ritorna stringa vuota se non esiste."""
    p = PROMPTS_DIR / name
    return p.read_text().strip() if p.exists() else ""


def _build_system_prompt(object_type):
    """Combina base_system.txt con il prompt specifico per il tipo di oggetto."""
    base = _load_prompt_file("base_system.txt")
    specific = _load_prompt_file(f"{object_type}.txt")
    structure = (
        "STRUTTURA RICHIESTA: Definisci variabili parametriche all'inizio "
        "(es: width=50; height=30;). "
        "Metti tutta la geometria in un modulo chiamato main_object(). "
        "Ultima riga del file: main_object(); "
        "NON usare include<> o use<>. Il file deve essere self-contained."
    )
    parts = [p for p in [base, specific, structure] if p]
    return "\n\n".join(parts)


def _extract_bounding_box_from_stl(stl_path):
    """
    Estrae bounding box da un file STL ASCII parsando le coordinate vertex.
    Ritorna dict {x, y, z, min, max} oppure None in caso di errore.
    """
    try:
        content = Path(stl_path).read_text(errors="replace")
        xs, ys, zs = [], [], []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("vertex "):
                parts = line.split()
                if len(parts) == 4:
                    xs.append(float(parts[1]))
                    ys.append(float(parts[2]))
                    zs.append(float(parts[3]))
        if not xs:
            return None
        return {
            "x": round(max(xs) - min(xs), 3),
            "y": round(max(ys) - min(ys), 3),
            "z": round(max(zs) - min(zs), 3),
            "min": {"x": round(min(xs), 3), "y": round(min(ys), 3), "z": round(min(zs), 3)},
            "max": {"x": round(max(xs), 3), "y": round(max(ys), 3), "z": round(max(zs), 3)},
        }
    except Exception as e:
        log(f"Bounding box extraction error: {e}", "WARN")
        return None


def do_compile_scad(scad_path, output_name, config):
    """Compila un file .scad in .stl tramite openscad. Ritorna dict con risultato."""
    scad_path = Path(scad_path)
    MODELS_STL_DIR.mkdir(parents=True, exist_ok=True)

    stem = Path(output_name).stem if output_name else scad_path.stem
    stl_path = MODELS_STL_DIR / f"{stem}.stl"

    openscad_bin = config.get("openscad_binary", "openscad")
    stl_format = config.get("stl_format", "asciistl")
    timeout = config.get("openscad_timeout", 300)

    cmd = [openscad_bin, "--export-format", stl_format, "-o", str(stl_path), str(scad_path)]
    log(f"🔧 Compilando: {' '.join(cmd)}")

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        compile_log = (p.stdout + p.stderr).strip()
        success = p.returncode == 0 and stl_path.exists()
        file_size_kb = round(stl_path.stat().st_size / 1024, 2) if stl_path.exists() else 0

        if not success:
            log(f"OpenSCAD error (rc={p.returncode}): {compile_log}", "ERROR")

        return {
            "stl_file": str(stl_path) if success else None,
            "success": success,
            "compile_log": compile_log,
            "file_size_kb": file_size_kb,
        }
    except subprocess.TimeoutExpired:
        log(f"OpenSCAD timeout dopo {timeout}s", "ERROR")
        return {
            "stl_file": None,
            "success": False,
            "compile_log": f"Timeout after {timeout}s",
            "file_size_kb": 0,
        }
    except FileNotFoundError:
        log(f"openscad non trovato: {openscad_bin}", "ERROR")
        return {
            "stl_file": None,
            "success": False,
            "compile_log": "openscad binary not found",
            "file_size_kb": 0,
        }


def handle_generate_3d(task, task_id, config):
    description = task.get("description", "")
    parameters = task.get("parameters", {})
    object_type = task.get("object_type", "simple")
    quality = task.get("quality", config.get("default_quality", "medium"))

    if object_type not in ("mechanical", "decorative", "simple"):
        object_type = "simple"
    if quality not in ("fast", "medium", "high"):
        quality = "medium"

    quality_presets = config.get("quality_presets", DEFAULT_CONFIG["quality_presets"])
    fn_value = quality_presets.get(quality, {}).get("fn", 64)
    dims = config.get("default_dimensions", {"max_x": 200, "max_y": 200, "max_z": 200})

    system_prompt = _build_system_prompt(object_type)

    # Costruzione prompt utente
    user_parts = [f"Genera un modello OpenSCAD per: {description}"]
    if parameters:
        params_str = "\n".join(f"  - {k}: {v}" for k, v in parameters.items())
        user_parts.append(f"Parametri specificati:\n{params_str}")
    user_parts.append(
        f"Qualità: {quality} ($fn={fn_value}). "
        f"Bounding box massimo: {dims['max_x']}x{dims['max_y']}x{dims['max_z']}mm."
    )
    user_prompt = "\n".join(user_parts)

    log(f"🤖 Chiamata Ollama per generate_3d (type={object_type}, quality={quality}, fn={fn_value})")
    raw_response = ask_ollama(user_prompt, config, system_prompt=system_prompt)

    if not raw_response:
        return {
            "success": False,
            "error_message": "Nessuna risposta da Ollama",
            "scad_file": None,
            "stl_file": None,
        }

    scad_code = clean_llm(raw_response)

    # Validazione pre-compilazione: controlla presenza di primitivi OpenSCAD o moduli
    geom_primitives = ("cube(", "cylinder(", "sphere(", "polyhedron(", "module ")
    if not any(kw in scad_code for kw in geom_primitives):
        log("⚠️ Codice OpenSCAD sospetto — potrebbe non essere valido", "WARN")
        # Compila comunque: l'LLM potrebbe usare funzioni custom non in questa lista

    # Salva il file .scad
    MODELS_SCAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scad_filename = f"{task_id}_{timestamp}.scad"
    scad_path = MODELS_SCAD_DIR / scad_filename
    scad_path.write_text(scad_code)
    log(f"💾 SCAD salvato: {scad_path}")

    # Compilazione principale
    compile_result = do_compile_scad(scad_path, scad_filename, config)

    # Auto-correzione: se la compilazione fallisce, invia codice + errore a Ollama
    auto_corrected = False
    if not compile_result["success"]:
        error_msg = compile_result.get("compile_log", "errore sconosciuto")
        log(f"🔧 Compilazione fallita — tentativo auto-correzione")
        correction_prompt = (
            f"Il seguente codice OpenSCAD genera questo errore:\n"
            f"{error_msg}\n\n"
            f"Codice originale:\n{scad_code}\n\n"
            f"Correggi il codice. Rispondi SOLO con il codice OpenSCAD corretto e completo."
        )
        corrected_raw = ask_ollama(correction_prompt, config, system_prompt=system_prompt)
        if corrected_raw:
            corrected_code = clean_llm(corrected_raw)
            if corrected_code and corrected_code != scad_code:
                scad_path.write_text(corrected_code)
                compile_result = do_compile_scad(scad_path, scad_filename, config)
                auto_corrected = True
                if compile_result["success"]:
                    log("🔧 Auto-correzione applicata con successo")
                else:
                    log("🔧 Auto-correzione applicata — compilazione ancora fallita", "WARN")

    # Estrazione bounding box dopo compilazione riuscita
    dimensions = None
    if compile_result["success"] and compile_result.get("stl_file"):
        dimensions = _extract_bounding_box_from_stl(compile_result["stl_file"])
        if dimensions:
            log(f"📐 Bounding box: {dimensions['x']}×{dimensions['y']}×{dimensions['z']} mm")

    return {
        "success": compile_result["success"],
        "scad_file": str(scad_path),
        "stl_file": compile_result.get("stl_file"),
        "error_message": None if compile_result["success"] else compile_result.get("compile_log", ""),
        "compile_log": compile_result.get("compile_log", ""),
        "file_size_kb": compile_result.get("file_size_kb", 0),
        "auto_corrected": auto_corrected,
        "dimensions": dimensions,
    }


def handle_compile_scad(task, config):
    scad_file = task.get("scad_file", "")
    output_name = task.get("output_name")

    if not scad_file:
        return {"success": False, "stl_file": None, "compile_log": "scad_file mancante", "file_size_kb": 0}

    scad_path = Path(scad_file).expanduser()
    if not scad_path.exists():
        return {
            "success": False,
            "stl_file": None,
            "compile_log": f"File non trovato: {scad_path}",
            "file_size_kb": 0,
        }

    return do_compile_scad(scad_path, output_name, config)


def handle_validate_scad(task, config):
    scad_file = task.get("scad_file", "")

    if not scad_file:
        return {"valid": False, "warnings": [], "errors": ["scad_file mancante"]}

    scad_path = Path(scad_file).expanduser()
    if not scad_path.exists():
        return {"valid": False, "warnings": [], "errors": [f"File non trovato: {scad_path}"]}

    openscad_bin = config.get("openscad_binary", "openscad")
    timeout = config.get("openscad_timeout", 300)

    try:
        p = subprocess.run(
            [openscad_bin, "--check-parameter-ranges", str(scad_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (p.stdout + p.stderr).strip()
        lines = output.splitlines() if output else []
        warnings = [l for l in lines if "WARNING" in l.upper()]
        errors = [l for l in lines if "ERROR" in l.upper()]
        return {"valid": p.returncode == 0, "warnings": warnings, "errors": errors}
    except subprocess.TimeoutExpired:
        return {"valid": False, "warnings": [], "errors": [f"Timeout after {timeout}s"]}
    except FileNotFoundError:
        return {"valid": False, "warnings": [], "errors": ["openscad binary not found"]}


def handle_list_models():
    if not MODELS_STL_DIR.exists():
        return {"models": []}

    models = []
    for stl in sorted(MODELS_STL_DIR.glob("*.stl"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = stl.stat()
        scad_available = (MODELS_SCAD_DIR / (stl.stem + ".scad")).exists()
        models.append({
            "filename": stl.name,
            "size_kb": round(stat.st_size / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "scad_available": scad_available,
        })

    return {"models": models}

# =========================
# TASK CORE
# =========================

def should_stop(task, task_type, success, config):
    if success:
        return False
    if task.get("stop_on_fail") is True:
        return True
    if task_type == "test" and config.get("stop_on_test_fail"):
        return True
    return False


def process_task(task_file, config):
    with open(task_file) as f:
        task = json.load(f)

    task_id = task.get("id", task_file.stem)
    task_type = task.get("type", "prompt")
    retry = task.get("_retry", 0)

    log(f"▶ Task {task_id} [{task_type}]")
    update_status(task_id, task_type, "running")

    result = {"task_id": task_id, "type": task_type}
    success = False

    # ---- 3D TASK TYPES ----

    if task_type == "generate_3d":
        res = handle_generate_3d(task, task_id, config)
        result.update(res)
        success = res.get("success", False)

    elif task_type == "compile_scad":
        res = handle_compile_scad(task, config)
        result.update(res)
        success = res.get("success", False)

    elif task_type == "validate_scad":
        res = handle_validate_scad(task, config)
        result.update(res)
        success = res.get("valid", False)

    elif task_type == "list_models":
        res = handle_list_models()
        result.update(res)
        success = True

    # ---- LEGACY TASK TYPES ----

    elif task_type == "bash":
        prompt = task.get("prompt", "")
        llm_prompt = (
            "RISPONDI SOLO CON IL COMANDO, NIENTE ALTRO.\n"
            "NO introduzioni, NO spiegazioni, NO commenti, NO markdown.\n"
            "Genera il comando bash per:\n"
            f"{prompt}"
        )
        llm = ask_ollama(llm_prompt, config)
        cmd = clean_llm(llm).splitlines()[0]
        res = exec_bash(cmd)
        result["steps"] = [{"cmd": cmd, "result": res}]
        success = res["success"]

    elif task_type == "python":
        prompt = task.get("prompt", "")
        llm_prompt = (
            "RISPONDI SOLO CON IL CODICE, NIENTE ALTRO.\n"
            "NO introduzioni, NO spiegazioni, NO markdown ```.\n"
            "Scrivi il codice python per:\n"
            f"{prompt}"
        )
        llm = ask_ollama(llm_prompt, config)
        code = clean_llm(llm)
        res = exec_python(code)
        result["steps"] = [{"code": code, "result": res}]
        success = res["success"]

    elif task_type == "file":
        user_prompt = task.get("prompt", "")
        llm_prompt = (
            "RISPONDI SOLO CON IL CONTENUTO DEL FILE, NIENTE ALTRO.\n"
            "NO introduzioni come 'Ecco', 'Certamente', 'Here is'.\n"
            "NO spiegazioni finali, NO markdown ```.\n"
            f"{user_prompt}"
        )
        content = ask_ollama(llm_prompt, config)
        res = write_file(task["filepath"], clean_llm(content))
        result["steps"] = [res]
        success = res["success"]

    elif task_type == "test":
        res = exec_bash(task.get("test_command", ""))
        expected = task.get("expected", "")
        actual = res.get("stdout", "").strip()
        success = expected in actual if expected else res["success"]
        result["steps"] = [{"expected": expected, "actual": actual}]

    elif task_type == "prompt":
        prompt = task.get("prompt", "")
        response = ask_ollama(prompt, config)
        result["response"] = response
        success = response is not None

    else:
        result["error"] = f"Unknown task type: {task_type}"

    # ---- RESULT ----

    result["success"] = success
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / f"{task_id}_{int(time.time())}.json", "w") as f:
        json.dump(result, f, indent=2)

    stop = should_stop(task, task_type, success, config)

    if not success and retry < config["max_retries"]:
        task["_retry"] = retry + 1
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        log(f"🔁 Retry {task['_retry']}/{config['max_retries']} for {task_id}", "WARN")
        return {"stop": stop}

    # move to done
    done = TASKS_DIR / "done"
    done.mkdir(exist_ok=True)
    task_file.rename(done / task_file.name)

    log(f"{'✅' if success else '❌'} Task {task_id}")
    update_status(None, None, "idle")

    return {"stop": stop}

# =========================
# MAIN LOOP
# =========================

def get_pending():
    tasks = []
    for f in TASKS_DIR.glob("*.json"):
        try:
            with open(f) as jf:
                prio = json.load(jf).get("priority", 10)
        except Exception:
            prio = 10
        tasks.append((prio, f))
    tasks.sort(key=lambda x: x[0])
    return [t[1] for t in tasks]


def main():
    log("🐼 PANDA 3D Worker avviato")
    save_default_config()
    update_status()

    while True:
        try:
            config = load_config()
            pending = get_pending()

            for task_file in pending:
                res = process_task(task_file, config)
                if res.get("stop"):
                    log("🛑 Pipeline fermata da gate", "WARN")
                    break

            time.sleep(config["check_interval"])

        except KeyboardInterrupt:
            log("PANDA fermato")
            break
        except Exception as e:
            log(f"Worker crash: {e}", "ERROR")
            time.sleep(10)


if __name__ == "__main__":
    main()
