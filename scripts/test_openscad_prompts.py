#!/usr/bin/env python3
"""
PANDA 3D — Test & Validazione Prompt OpenSCAD
==============================================

Testa che l'LLM generi codice OpenSCAD valido per diversi tipi di oggetti.

Per ogni test case:
1. Invia il prompt a Ollama (via ask_ollama del worker)
2. Salva il codice in ~/panda/models/scad/test_{name}.scad
3. Compila con openscad --export-format asciistl
4. Verifica STL creato e size > 0
5. Logga: PASS/FAIL, tempo, dimensione STL, warning OpenSCAD

Output: ~/panda/results/prompt_test_{timestamp}.json
"""

import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths (identici al worker)
# ---------------------------------------------------------------------------

PANDA_HOME   = Path.home() / "panda"
CONFIG_FILE  = PANDA_HOME / "config" / "panda.json"
PROMPTS_DIR  = PANDA_HOME / "prompts"
SCAD_DIR     = PANDA_HOME / "models" / "scad"
STL_DIR      = PANDA_HOME / "models" / "stl"
RESULTS_DIR  = PANDA_HOME / "results"

# ---------------------------------------------------------------------------
# Default config (specchio esatto del worker)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434",
    "model": "qwen2.5-coder:14b-instruct-q4_K_M",
    "model_fallback": "qwen2.5-coder:7b-instruct-q8_0",
    "openscad_binary": "openscad",
    "openscad_timeout": 300,
    "stl_format": "asciistl",
    "quality_presets": {
        "fast":   {"fn": 32,  "detail_level": "low"},
        "medium": {"fn": 64,  "detail_level": "medium"},
        "high":   {"fn": 128, "detail_level": "high"},
    },
    "default_dimensions": {"max_x": 200, "max_y": 200, "max_z": 200},
}

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "name": "cubo_semplice",
        "description": "cubo semplice 20x20x20mm",
        "object_type": "simple",
        "quality": "fast",
        "expected_keywords": ["cube", "translate"],
    },
    {
        "name": "cilindro_foro",
        "description": "cilindro con foro passante diametro 30mm, foro centrale da 10mm",
        "object_type": "mechanical",
        "quality": "fast",
        "expected_keywords": ["cylinder", "difference"],
    },
    {
        "name": "supporto_bobina",
        "description": "supporto per bobine di filamento 1kg, diametro esterno 200mm, diametro foro centrale 52mm, spessore disco 5mm",
        "object_type": "mechanical",
        "quality": "medium",
        "expected_keywords": ["cylinder", "difference"],
    },
    {
        "name": "vaso_ondulato",
        "description": "vaso cilindrico con pareti ondulate usando sin(), altezza 100mm, diametro base 60mm, spessore pareti 2mm",
        "object_type": "decorative",
        "quality": "medium",
        "expected_keywords": ["module", "cylinder"],
    },
    {
        "name": "ingranaggio",
        "description": "ingranaggio a denti dritti, 20 denti, modulo 2, spessore 10mm, foro asse 5mm",
        "object_type": "mechanical",
        "quality": "fast",
        "expected_keywords": ["module", "for", "cylinder"],
    },
    {
        "name": "portapenne",
        "description": "portapenne da scrivania con 6 fori da 12mm di diametro, disposizione circolare, altezza 120mm, base quadrata 90x90mm",
        "object_type": "simple",
        "quality": "fast",
        "expected_keywords": ["cylinder", "difference", "for"],
    },
]

# ---------------------------------------------------------------------------
# Utilities (riprese dal worker)
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f"[WARN] Config load error: {e} — using defaults")
    return DEFAULT_CONFIG.copy()


def _load_prompt_file(name: str) -> str:
    p = PROMPTS_DIR / name
    return p.read_text().strip() if p.exists() else ""


def _build_system_prompt(object_type: str) -> str:
    base = _load_prompt_file("base_system.txt")
    specific = _load_prompt_file(f"{object_type}.txt")
    # Istruzione strutturale aggiuntiva (stessa che viene iniettata in handle_generate_3d)
    structure_instruction = (
        "STRUTTURA RICHIESTA: Definisci variabili parametriche all'inizio "
        "(es: width=50; height=30;). "
        "Metti tutta la geometria in un modulo chiamato main_object(). "
        "Ultima riga del file: main_object(); "
        "NON usare include<> o use<>. Il file deve essere self-contained."
    )
    parts = [p for p in [base, specific, structure_instruction] if p]
    return "\n\n".join(parts)


def ask_ollama(prompt: str, config: dict, system_prompt: str | None = None) -> str | None:
    """Identica al worker: chiama Ollama e restituisce la risposta testuale."""
    start = time.time()
    stop_evt = threading.Event()

    def _ticker():
        while not stop_evt.wait(30):
            elapsed = time.time() - start
            print(f"  ⏳ Ollama elabora... ({int(elapsed//60)}m{int(elapsed%60):02d}s)", flush=True)

    ticker = threading.Thread(target=_ticker, daemon=True)
    ticker.start()
    try:
        if system_prompt:
            r = requests.post(
                f"{config['ollama_url']}/api/chat",
                json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": prompt},
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
        print(f"  [ERROR] Ollama error: {e}")
        return None
    finally:
        stop_evt.set()
        ticker.join(timeout=1)


def clean_llm(code: str) -> str:
    """Rimuove prefazioni e blocchi markdown (identico al worker)."""
    import re
    if not code:
        return ""
    code = code.strip()

    preface_patterns = [
        r"^[Ee]cco\s+(il|lo|la|i|gli|le|qui|qua)?\s*[^:]*[:\.]?\s*\n?",
        r"^[Cc]ertamente[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Ss]icuramente[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Dd]i seguito[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Qq]ui (c'è|ci sono|trovi)[^:]*[:\.]?\s*\n?",
        r"^[Ii]l (codice|comando|contenuto|file)[^:]*[:\.]?\s*\n?",
        r"^[Cc]ome richiesto[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Hh]ere['\u2019]?s?\s+(is|are)?\s*[^:]*[:\.]?\s*\n?",
        r"^[Ss]ure[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Cc]ertainly[,\.]?\s*[^:]*[:\.]?\s*\n?",
        r"^[Tt]he (code|command|content|file)[^:]*[:\.]?\s*\n?",
        r"^[Bb]elow[^:]*[:\.]?\s*\n?",
        r"^[Aa]s requested[,\.]?\s*[^:]*[:\.]?\s*\n?",
    ]
    for pat in preface_patterns:
        code = re.sub(pat, "", code, count=1)
    code = code.strip()

    md = re.match(r"^```[\w\-]*\s*\n?([\s\S]*?)```\s*$", code, re.DOTALL)
    if md:
        code = md.group(1).strip()
    elif code.startswith("```"):
        parts = code.split("```")
        if len(parts) >= 2:
            lines = parts[1].split("\n", 1)
            code = lines[1].strip() if len(lines) > 1 else parts[1].strip()

    return code.strip()


# ---------------------------------------------------------------------------
# OpenSCAD compilation
# ---------------------------------------------------------------------------

def compile_scad(scad_path: Path, stl_path: Path, config: dict) -> dict:
    """
    Compila il file SCAD e ritorna un dict con:
      success, file_size_kb, compile_log, warnings, returncode
    """
    openscad_bin = config.get("openscad_binary", "openscad")
    stl_format   = config.get("stl_format", "asciistl")
    timeout      = config.get("openscad_timeout", 300)

    cmd = [openscad_bin, "--export-format", stl_format, "-o", str(stl_path), str(scad_path)]

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        compile_log = (p.stdout + p.stderr).strip()
        warnings    = [l for l in compile_log.splitlines() if "WARNING" in l.upper()]
        errors_log  = [l for l in compile_log.splitlines() if "ERROR"   in l.upper()]
        success     = p.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0
        size_kb     = round(stl_path.stat().st_size / 1024, 2) if stl_path.exists() else 0.0
        return {
            "success":    success,
            "returncode": p.returncode,
            "file_size_kb": size_kb,
            "compile_log": compile_log,
            "warnings":   warnings,
            "errors_log": errors_log,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "returncode": -1,
            "file_size_kb": 0, "compile_log": f"Timeout dopo {timeout}s",
            "warnings": [], "errors_log": [f"Timeout dopo {timeout}s"],
        }
    except FileNotFoundError:
        return {
            "success": False, "returncode": -1,
            "file_size_kb": 0,
            "compile_log": f"Binario openscad non trovato: {openscad_bin}",
            "warnings": [], "errors_log": ["openscad non trovato"],
        }


# ---------------------------------------------------------------------------
# Single test runner
# ---------------------------------------------------------------------------

def run_test(tc: dict, config: dict) -> dict:
    """Esegue un singolo test case, ritorna un dict con tutti i dettagli."""
    name         = tc["name"]
    description  = tc["description"]
    object_type  = tc.get("object_type", "simple")
    quality      = tc.get("quality", "fast")
    exp_keywords = tc.get("expected_keywords", [])

    quality_presets = config.get("quality_presets", DEFAULT_CONFIG["quality_presets"])
    fn_value = quality_presets.get(quality, {}).get("fn", 32)
    dims     = config.get("default_dimensions", DEFAULT_CONFIG["default_dimensions"])

    print(f"\n{'─'*60}")
    print(f"▶ TEST: {name}")
    print(f"  Descrizione: {description}")
    print(f"  Tipo: {object_type} | Qualità: {quality} ($fn={fn_value})")

    result = {
        "name":        name,
        "description": description,
        "object_type": object_type,
        "quality":     quality,
        "fn":          fn_value,
        "status":      "FAIL",
        "pass":        False,
        "elapsed_s":   0.0,
        "llm_response_chars": 0,
        "scad_path":   None,
        "stl_path":    None,
        "file_size_kb": 0.0,
        "warnings":    [],
        "errors":      [],
        "compile_log": "",
        "keyword_check": {},
        "failure_reason": None,
    }

    t0 = time.time()

    # ── 1. Build prompts ──────────────────────────────────────────────────
    system_prompt = _build_system_prompt(object_type)
    user_prompt = (
        f"Genera un modello OpenSCAD per: {description}\n"
        f"Qualità: {quality} ($fn={fn_value}). "
        f"Bounding box massimo: {dims['max_x']}x{dims['max_y']}x{dims['max_z']}mm."
    )

    # ── 2. Ask Ollama ─────────────────────────────────────────────────────
    print(f"  Chiamata Ollama...", flush=True)
    raw = ask_ollama(user_prompt, config, system_prompt=system_prompt)

    if not raw:
        result["failure_reason"] = "Nessuna risposta da Ollama"
        result["elapsed_s"] = round(time.time() - t0, 1)
        print(f"  ❌ FAIL — {result['failure_reason']}")
        return result

    result["llm_response_chars"] = len(raw)
    scad_code = clean_llm(raw)

    # ── 3. Keyword check (validazione sintattica base) ────────────────────
    kw_check = {kw: (kw in scad_code) for kw in exp_keywords}
    result["keyword_check"] = kw_check
    missing_kw = [kw for kw, found in kw_check.items() if not found]
    if missing_kw:
        print(f"  ⚠ Keyword mancanti: {missing_kw}")

    openscad_primitives = ("module", "cube", "cylinder", "sphere",
                           "union", "difference", "intersection", "rotate", "translate")
    if not any(kw in scad_code for kw in openscad_primitives):
        result["failure_reason"] = "Risposta LLM non contiene codice OpenSCAD riconoscibile"
        result["elapsed_s"] = round(time.time() - t0, 1)
        print(f"  ❌ FAIL — {result['failure_reason']}")
        return result

    # ── 4. Salva .scad ────────────────────────────────────────────────────
    SCAD_DIR.mkdir(parents=True, exist_ok=True)
    STL_DIR.mkdir(parents=True, exist_ok=True)

    scad_path = SCAD_DIR / f"test_{name}.scad"
    stl_path  = STL_DIR  / f"test_{name}.stl"
    scad_path.write_text(scad_code, encoding="utf-8")
    result["scad_path"] = str(scad_path)
    print(f"  💾 SCAD salvato: {scad_path.name} ({len(scad_code)} chars)")

    # ── 5. Compila ───────────────────────────────────────────────────────
    print(f"  🔧 Compilazione OpenSCAD...", flush=True)
    cr = compile_scad(scad_path, stl_path, config)

    result["compile_log"]  = cr["compile_log"]
    result["warnings"]     = cr["warnings"]
    result["errors"]       = cr.get("errors_log", [])
    result["file_size_kb"] = cr["file_size_kb"]
    result["elapsed_s"]    = round(time.time() - t0, 1)

    if cr["warnings"]:
        for w in cr["warnings"][:3]:
            print(f"  ⚠ {w}")

    # ── 6. Verifica STL ───────────────────────────────────────────────────
    if cr["success"] and stl_path.exists() and stl_path.stat().st_size > 0:
        result["stl_path"]   = str(stl_path)
        result["status"]     = "PASS"
        result["pass"]       = True
        print(f"  ✅ PASS  — STL: {cr['file_size_kb']} KB  |  tempo: {result['elapsed_s']}s")
        if missing_kw:
            print(f"     (keyword mancanti {missing_kw} ma compilazione OK)")
    else:
        result["failure_reason"] = (
            f"Compilazione fallita (rc={cr['returncode']}): "
            f"{cr['compile_log'][:200]}"
        )
        print(f"  ❌ FAIL — {result['failure_reason'][:120]}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  PANDA 3D — Test Prompt OpenSCAD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = load_config()
    print(f"\nConfig: model={config['model']}  ollama={config['ollama_url']}")

    # Verifica raggiungibilità Ollama prima di partire
    try:
        r = requests.get(f"{config['ollama_url']}/api/tags", timeout=10)
        r.raise_for_status()
        print(f"✓ Ollama raggiungibile")
    except Exception as e:
        print(f"✗ Ollama non raggiungibile: {e}")
        print("  Avvia Ollama con: ollama serve")
        sys.exit(1)

    # Verifica openscad
    openscad_bin = config.get("openscad_binary", "openscad")
    try:
        proc = subprocess.run([openscad_bin, "--version"], capture_output=True, text=True, timeout=10)
        ver  = (proc.stdout + proc.stderr).strip().splitlines()[0] if (proc.stdout + proc.stderr).strip() else "?"
        print(f"✓ OpenSCAD: {ver}")
    except FileNotFoundError:
        print(f"✗ OpenSCAD non trovato: {openscad_bin}")
        print("  Installa con: sudo apt install openscad")
        sys.exit(1)

    # Selezione test cases da CLI (opzionale: ./test_openscad_prompts.py cubo_semplice ingranaggio)
    selected_names = sys.argv[1:]
    test_cases = TEST_CASES
    if selected_names:
        test_cases = [tc for tc in TEST_CASES if tc["name"] in selected_names]
        if not test_cases:
            print(f"\n[ERROR] Nessun test case trovato per: {selected_names}")
            print(f"  Disponibili: {[tc['name'] for tc in TEST_CASES]}")
            sys.exit(1)
        print(f"\nTest selezionati: {[tc['name'] for tc in test_cases]}")

    # Esecuzione
    results = []
    total_t0 = time.time()

    for tc in test_cases:
        res = run_test(tc, config)
        results.append(res)

    # ── Riepilogo ────────────────────────────────────────────────────────
    total_elapsed = round(time.time() - total_t0, 1)
    passed  = sum(1 for r in results if r["pass"])
    failed  = len(results) - passed
    avg_stl = round(sum(r["file_size_kb"] for r in results if r["pass"]) / max(passed, 1), 1)

    print(f"\n{'=' * 60}")
    print(f"  RISULTATI FINALI")
    print(f"{'=' * 60}")
    for r in results:
        icon = "✅" if r["pass"] else "❌"
        warn = f"  ⚠{len(r['warnings'])}w" if r["warnings"] else ""
        kw_fail = [k for k, v in r.get("keyword_check", {}).items() if not v]
        kw_note = f"  kw_miss:{kw_fail}" if kw_fail else ""
        print(
            f"  {icon} {r['name']:<22} "
            f"{r['elapsed_s']:>6.1f}s  "
            f"{r['file_size_kb']:>7.1f} KB{warn}{kw_note}"
        )
    print(f"{'─' * 60}")
    print(f"  PASS: {passed}/{len(results)}   FAIL: {failed}   tempo totale: {total_elapsed}s")
    print(f"  Dimensione media STL (PASS): {avg_stl} KB")

    # ── Salva JSON ───────────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = RESULTS_DIR / f"prompt_test_{ts}.json"
    report = {
        "run_at":       datetime.now().isoformat(),
        "model":        config["model"],
        "ollama_url":   config["ollama_url"],
        "total_tests":  len(results),
        "passed":       passed,
        "failed":       failed,
        "total_elapsed_s": total_elapsed,
        "avg_stl_kb_pass": avg_stl,
        "results":      results,
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📄 Report JSON salvato: {out_path}")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
