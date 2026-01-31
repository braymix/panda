#!/usr/bin/env python3
"""
PANDA Worker v3.1
Pana Automating Never Death (on) Afterwork

Features:
- Task execution (bash, python, file, test)
- Retry automatico
- Pipeline stop su gate fallito
- Stato live per dashboard
- Long-running safe
"""

import json
import sys
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

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

# =========================
# CONFIG
# =========================

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434",
    "model": "qwen2.5-coder:3b",
    "check_interval": 10,
    "max_retries": 3,
    "execute_bash": True,
    "execute_code": True,
    "modify_files": True,
    "stop_on_test_fail": False
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

def update_status(task_id=None, task_type=None, status="idle", progress=None):
    STATUS_DIR.mkdir(exist_ok=True)
    payload = {
        "current_task": task_id,
        "task_type": task_type,
        "status": status,
        "progress": progress,
        "updated_at": datetime.now().isoformat()
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

def ask_ollama(prompt, config):
    try:
        r = requests.post(
            f"{config['ollama_url']}/api/generate",
            json={"model": config["model"], "prompt": prompt, "stream": False},
            timeout=900
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        log(f"Ollama error: {e}", "ERROR")
        return None

def clean_llm(code):
    if not code:
        return ""
    code = code.strip()
    if code.startswith("```"):
        code = code.split("```")[1]
    return code.strip()

# =========================
# EXECUTION
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

    log(f"▶ Task {task_id}")
    update_status(task_id, task_type, "running")

    result = {"task_id": task_id, "type": task_type, "steps": []}
    success = False

    # ---- TASK TYPES ----

    if task_type == "bash":
        prompt = task.get("prompt", "")
        llm = ask_ollama(f"Genera SOLO comando bash:\n{prompt}", config)
        cmd = clean_llm(llm).splitlines()[0]
        res = exec_bash(cmd)
        result["steps"].append({"cmd": cmd, "result": res})
        success = res["success"]

    elif task_type == "python":
        prompt = task.get("prompt", "")
        llm = ask_ollama(f"Genera SOLO codice python:\n{prompt}", config)
        code = clean_llm(llm)
        res = exec_python(code)
        result["steps"].append({"code": code, "result": res})
        success = res["success"]

    elif task_type == "file":
        content = ask_ollama(task.get("prompt", ""), config)
        res = write_file(task["filepath"], clean_llm(content))
        result["steps"].append(res)
        success = res["success"]

    elif task_type == "test":
        res = exec_bash(task.get("test_command", ""))
        expected = task.get("expected", "")
        actual = res.get("stdout", "").strip()
        success = expected in actual if expected else res["success"]
        result["steps"].append({"expected": expected, "actual": actual})

    else:
        result["error"] = f"Unknown task type {task_type}"

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
        log(f"🔁 Retry {task['_retry']} for {task_id}", "WARN")
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
        with open(f) as jf:
            prio = json.load(jf).get("priority", 10)
        tasks.append((prio, f))
    tasks.sort(key=lambda x: x[0])
    return [t[1] for t in tasks]

def main():
    log("🐼 PANDA Worker v3.1 avviato")
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

