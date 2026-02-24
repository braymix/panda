#!/usr/bin/env bash
# =============================================================================
# PANDA 3D — Script di Avvio Completo
# =============================================================================
# Uso:
#   ./start_panda3d.sh              avvio normale con tail dei log
#   ./start_panda3d.sh --no-tail   avvio senza follow dei log
#   ./start_panda3d.sh --check     solo verifica dipendenze, senza avvio
# =============================================================================

set -euo pipefail

# ── Configurazione ─────────────────────────────────────────────────────────
PANDA_HOME="${HOME}/panda"
OLLAMA_URL="http://localhost:11434"
DASHBOARD_URL="http://localhost:5000"
LOG_DIR="${PANDA_HOME}/logs"
CONFIG_FILE="${PANDA_HOME}/config/panda.json"

# Leggi modello da config (fallback al default)
if command -v python3 &>/dev/null && [[ -f "${CONFIG_FILE}" ]]; then
    LLM_MODEL=$(python3 -c "
import json, sys
try:
    cfg = json.load(open('${CONFIG_FILE}'))
    print(cfg.get('model', 'qwen2.5-coder:14b-instruct-q4_K_M'))
except: print('qwen2.5-coder:14b-instruct-q4_K_M')
" 2>/dev/null)
    LLM_FALLBACK=$(python3 -c "
import json, sys
try:
    cfg = json.load(open('${CONFIG_FILE}'))
    print(cfg.get('model_fallback', 'qwen2.5-coder:7b-instruct-q8_0'))
except: print('qwen2.5-coder:7b-instruct-q8_0')
" 2>/dev/null)
else
    LLM_MODEL="qwen2.5-coder:14b-instruct-q4_K_M"
    LLM_FALLBACK="qwen2.5-coder:7b-instruct-q8_0"
fi

# ── Colori ─────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; BOLD=''; RESET=''
fi

# ── Argomenti ──────────────────────────────────────────────────────────────
NO_TAIL=0
CHECK_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --no-tail)  NO_TAIL=1 ;;
        --check)    CHECK_ONLY=1 ;;
        -h|--help)
            echo "Uso: $0 [--no-tail] [--check]"
            echo "  --no-tail   Avvia senza seguire i log"
            echo "  --check     Verifica dipendenze senza avviare"
            exit 0 ;;
    esac
done

# ── Helper ─────────────────────────────────────────────────────────────────
ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
info() { echo -e "  ${CYAN}→${RESET}  $*"; }

CHECKS_FAILED=0
require_ok() {
    if [[ $1 -ne 0 ]]; then
        CHECKS_FAILED=1
    fi
}

# ── Banner ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║        PANDA 3D — Avvio Sistema                  ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo -e "  $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── CHECK 1: Ollama running ─────────────────────────────────────────────────
echo -e "${BOLD}[1/4] Ollama${RESET}"
if curl -sf "${OLLAMA_URL}/api/tags" -o /dev/null --max-time 5 2>/dev/null; then
    ok "Ollama raggiungibile su ${OLLAMA_URL}"
else
    fail "Ollama NON raggiungibile su ${OLLAMA_URL}"
    info "Avvia con: ollama serve"
    info "Oppure: sudo systemctl start ollama"
    CHECKS_FAILED=1
fi

# ── CHECK 2: OpenSCAD installato ───────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] OpenSCAD${RESET}"

# Cerca il binario in path comuni
OPENSCAD_BIN=""
if command -v openscad &>/dev/null; then
    OPENSCAD_BIN="openscad"
elif command -v openscad-nightly &>/dev/null; then
    OPENSCAD_BIN="openscad-nightly"
elif [[ -f /usr/bin/openscad ]]; then
    OPENSCAD_BIN="/usr/bin/openscad"
elif [[ -f /usr/local/bin/openscad ]]; then
    OPENSCAD_BIN="/usr/local/bin/openscad"
elif [[ -f /snap/bin/openscad ]]; then
    OPENSCAD_BIN="/snap/bin/openscad"
fi

if [[ -n "${OPENSCAD_BIN}" ]]; then
    OPENSCAD_VER=$("${OPENSCAD_BIN}" --version 2>&1 | head -1 || echo "versione sconosciuta")
    ok "OpenSCAD trovato: ${OPENSCAD_BIN}"
    info "Versione: ${OPENSCAD_VER}"
else
    fail "OpenSCAD NON trovato"
    info "Installa con: sudo apt install openscad"
    info "Oppure: sudo snap install openscad"
    CHECKS_FAILED=1
fi

# ── CHECK 3: Modello LLM disponibile ───────────────────────────────────────
echo ""
echo -e "${BOLD}[3/4] Modello LLM${RESET}"
MODEL_OK=0
FALLBACK_OK=0

if curl -sf "${OLLAMA_URL}/api/tags" --max-time 5 2>/dev/null | \
   python3 -c "
import json, sys
data = json.load(sys.stdin)
names = [m.get('name','') for m in data.get('models',[])]
sys.exit(0 if any('${LLM_MODEL}'.split(':')[0] in n for n in names) else 1)
" 2>/dev/null; then
    ok "Modello principale disponibile: ${LLM_MODEL}"
    MODEL_OK=1
else
    warn "Modello principale non trovato: ${LLM_MODEL}"
    # Controlla fallback
    if curl -sf "${OLLAMA_URL}/api/tags" --max-time 5 2>/dev/null | \
       python3 -c "
import json, sys
data = json.load(sys.stdin)
names = [m.get('name','') for m in data.get('models',[])]
sys.exit(0 if any('${LLM_FALLBACK}'.split(':')[0] in n for n in names) else 1)
" 2>/dev/null; then
        ok "Modello fallback disponibile: ${LLM_FALLBACK}"
        FALLBACK_OK=1
    else
        fail "Nessun modello compatibile trovato"
        info "Scarica con: ollama pull ${LLM_MODEL}"
        info "Fallback:    ollama pull ${LLM_FALLBACK}"
        CHECKS_FAILED=1
    fi
fi

# ── CHECK 4: Cartelle e struttura progetto ─────────────────────────────────
echo ""
echo -e "${BOLD}[4/4] Struttura Progetto${RESET}"
REQUIRED_DIRS=(
    "${PANDA_HOME}"
    "${PANDA_HOME}/tasks"
    "${PANDA_HOME}/tasks/done"
    "${PANDA_HOME}/results"
    "${PANDA_HOME}/models/stl"
    "${PANDA_HOME}/models/scad"
    "${LOG_DIR}"
    "${PANDA_HOME}/config"
    "${PANDA_HOME}/status"
    "${PANDA_HOME}/dashboard"
)
ALL_DIRS_OK=1
for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ ! -d "${dir}" ]]; then
        mkdir -p "${dir}" && warn "Cartella creata: ${dir}" || { fail "Impossibile creare: ${dir}"; ALL_DIRS_OK=0; }
    fi
done
[[ $ALL_DIRS_OK -eq 1 ]] && ok "Struttura cartelle OK" || { fail "Alcune cartelle mancanti"; CHECKS_FAILED=1; }

if [[ -f "${CONFIG_FILE}" ]]; then
    ok "Config: ${CONFIG_FILE}"
else
    warn "Config non trovata: ${CONFIG_FILE}"
fi

if [[ -f "${PANDA_HOME}/worker.py" ]]; then
    ok "worker.py presente"
else
    fail "worker.py NON trovato in ${PANDA_HOME}"
    CHECKS_FAILED=1
fi

if [[ -f "${PANDA_HOME}/dashboard/server.py" ]]; then
    ok "dashboard/server.py presente"
else
    warn "dashboard/server.py non trovato"
fi

# ── Spazio disco ────────────────────────────────────────────────────────────
echo ""
DISK_FREE_KB=$(df -k "${PANDA_HOME}/models" 2>/dev/null | tail -1 | awk '{print $4}')
if [[ -n "${DISK_FREE_KB}" ]]; then
    DISK_FREE_GB=$(echo "scale=1; ${DISK_FREE_KB}/1048576" | bc 2>/dev/null || echo "?")
    if [[ "${DISK_FREE_KB}" -lt 512000 ]]; then
        warn "Spazio disco basso: ${DISK_FREE_GB} GB liberi in ~/panda/models/"
    else
        ok "Spazio disco: ${DISK_FREE_GB} GB liberi in ~/panda/models/"
    fi
fi

# ── Sommario check ──────────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────────"
if [[ ${CHECKS_FAILED} -eq 1 ]]; then
    echo -e "  ${RED}${BOLD}Verifica FALLITA — risolvi i problemi prima di avviare${RESET}"
    if [[ ${CHECK_ONLY} -eq 0 ]]; then
        echo -e "  Usa ${BOLD}--check${RESET} per solo diagnostica"
        exit 1
    fi
    exit 1
else
    echo -e "  ${GREEN}${BOLD}Tutte le verifiche OK — sistema pronto ✓${RESET}"
fi

[[ ${CHECK_ONLY} -eq 1 ]] && echo "" && exit 0

# ── Avvio Servizi ───────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Avvio servizi systemd...${RESET}"

if systemctl is-active --quiet panda 2>/dev/null; then
    info "Riavvio panda.service..."
    sudo systemctl restart panda && ok "panda.service riavviato" || fail "Errore riavvio panda.service"
else
    info "Avvio panda.service..."
    sudo systemctl start panda && ok "panda.service avviato" || {
        fail "Errore avvio panda.service"
        info "Controlla: sudo journalctl -u panda -n 30"
    }
fi

if systemctl is-active --quiet panda-dashboard 2>/dev/null; then
    info "Riavvio panda-dashboard.service..."
    sudo systemctl restart panda-dashboard && ok "panda-dashboard.service riavviato" || fail "Errore riavvio"
else
    info "Avvio panda-dashboard.service..."
    sudo systemctl start panda-dashboard && ok "panda-dashboard.service avviato" || {
        fail "Errore avvio panda-dashboard.service"
        info "Controlla: sudo journalctl -u panda-dashboard -n 30"
    }
fi

# ── Info finali ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║  PANDA 3D avviato!                               ║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║${RESET}  Dashboard:  ${CYAN}${DASHBOARD_URL}${RESET}"
echo -e "${BOLD}║${RESET}  Ollama:     ${CYAN}${OLLAMA_URL}${RESET}"
echo -e "${BOLD}║${RESET}  Modello:    ${LLM_MODEL}"
echo -e "${BOLD}║${RESET}  Log:        ${LOG_DIR}/"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo "  Comandi utili:"
echo "    sudo systemctl status panda"
echo "    sudo journalctl -u panda -f"
echo "    python3 ~/panda/scripts/check_system.py"
echo ""

# ── Tail log ────────────────────────────────────────────────────────────────
if [[ ${NO_TAIL} -eq 0 ]]; then
    TODAY=$(date '+%Y-%m-%d')
    LOG_FILE="${LOG_DIR}/${TODAY}.log"
    if [[ ! -f "${LOG_FILE}" ]]; then
        LOG_FILE="${LOG_DIR}/panda-stdout.log"
    fi

    echo -e "  ${BOLD}Log live: ${LOG_FILE}${RESET}  (Ctrl+C per uscire)"
    echo "──────────────────────────────────────────────────"
    sleep 1
    tail -f "${LOG_FILE}" 2>/dev/null || {
        echo -e "  ${YELLOW}Log non ancora disponibile. Attendo...${RESET}"
        sleep 3
        tail -f "${LOG_FILE}" 2>/dev/null || echo "  Log non trovato: ${LOG_FILE}"
    }
fi
