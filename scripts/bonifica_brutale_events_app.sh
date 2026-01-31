#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/panda/projects/events-app}"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$HOME/panda/bonifica-backup/$TS"

echo "[*] ROOT=$ROOT"
echo "[*] BACKUP=$BACKUP_DIR"

if [ ! -d "$ROOT" ]; then
  echo "[!] Directory non trovata: $ROOT" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
rsync -a --quiet \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'target/' \
  --exclude 'dist/' \
  --exclude 'build/' \
  --exclude '.idea/' \
  --exclude '.vscode/' \
  "$ROOT/" "$BACKUP_DIR/"

export ROOT_ARG="$ROOT"

python3 - <<'PY'
from pathlib import Path
import os, re

root = Path(os.environ["ROOT_ARG"]).expanduser()

BAD_PREFIXES = ("Ecco", "Di seguito", "Sure", "Here", "Il contenuto", "Ecco il contenuto")
SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".idea", ".vscode", "__pycache__"}
SKIP_EXTS = {
    ".png",".jpg",".jpeg",".gif",".webp",".ico",".pdf",
    ".zip",".gz",".tar",".7z",".rar",
    ".jar",".war",".class",".exe",".dll",".so",".dylib",
    ".woff",".woff2",".ttf",".otf",".eot",
    ".mp4",".mov",".mp3",".wav"
}

# Trova blocchi fenced. Se presenti: useremo SOLO il contenuto dentro i fence.
fence_re = re.compile(r"```[^\n]*\n([\s\S]*?)\n```", re.MULTILINE)

def is_skipped(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return path.suffix.lower() in SKIP_EXTS

def drop_any_triple_backticks_lines(text: str) -> str:
    # Rimuove QUALSIASI riga che contenga ```
    return "\n".join([l for l in text.splitlines() if "```" not in l])

def clean_text(txt: str) -> str:
    raw = txt.strip()

    # 0) se contiene fence blocks, prendo SOLO contenuto dentro (tutti i blocchi) e concateno
    blocks = fence_re.findall(raw)
    if blocks:
        merged = "\n\n".join(b.strip() for b in blocks if b.strip())
        merged = drop_any_triple_backticks_lines(merged)
        return (merged.strip() + "\n") if merged.strip() else "\n"

    # 1) altrimenti: rimuovi tutte le righe che contengono ```
    lines = drop_any_triple_backticks_lines(txt).splitlines()

    # 2) taglia preamboli tipo "Ecco..." e righe vuote iniziali
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s == "" or any(s.startswith(p) for p in BAD_PREFIXES):
            i += 1
            continue
        break

    cleaned = "\n".join(lines[i:]).strip()
    return (cleaned + "\n") if cleaned else "\n"

touched = 0
for p in root.rglob("*"):
    if not p.is_file():
        continue
    if is_skipped(p):
        continue

    try:
        original = p.read_text(errors="ignore")
    except Exception:
        continue

    new = clean_text(original)

    if new != original:
        p.write_text(new)
        touched += 1

print(f"[*] File modificati: {touched}")
PY

echo "[*] Gate: cerco ancora '```' ovunque (deve essere vuoto)"
if grep -R "```" -n "$ROOT" >/dev/null 2>&1; then
  echo "[!] Trovati ancora triple backticks. Prime 50 occorrenze:"
  grep -R "```" -n "$ROOT" | head -n 50
  exit 2
fi

echo "[✓] Bonifica brutale completata."
echo "[i] Backup pronto in: $BACKUP_DIR"
