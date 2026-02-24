# PANDA 3D

**P**ana **A**utomating **N**ever **D**eath (on) **A**fterwork — Generatore di Modelli 3D con AI

PANDA 3D è un sistema locale per la **generazione automatica di modelli 3D** stampabili. Prende in input una descrizione testuale, genera codice OpenSCAD tramite un LLM locale (Ollama + qwen2.5-coder), compila il modello in STL e lo rende disponibile via dashboard web.

---

## Architettura

```
Task JSON  →  worker.py  →  Ollama (LLM)  →  OpenSCAD  →  STL
                ↓                                           ↓
          Dashboard (Flask)  ←──────────────────────  ~/panda/models/
```

| Componente | Ruolo |
|---|---|
| `worker.py` | Loop principale: legge task, chiama LLM, compila SCAD |
| `dashboard/server.py` | API REST + UI web su porta 5000 |
| `config/panda.json` | Configurazione (modello, timeout, qualità) |
| `tasks/` | Coda task in attesa |
| `models/stl/` | STL generati |
| `models/scad/` | Sorgenti OpenSCAD generati |
| `results/` | Log JSON di ogni task eseguito |

---

## Quick Start

```bash
# 1. Verifica che tutto sia pronto
python3 ~/panda/scripts/check_system.py

# 2. Avvia worker e dashboard
sudo systemctl start panda panda-dashboard

# 3. Apri il browser
xdg-open http://localhost:5000
```

Oppure tutto in uno con lo script di avvio:

```bash
bash ~/panda/scripts/start_panda3d.sh
```

---

## Prerequisiti

| Dipendenza | Versione minima | Installazione |
|---|---|---|
| Python 3 | 3.10+ | già su Ubuntu 22+ |
| Ollama | qualsiasi | `curl -fsSL https://ollama.com/install.sh \| sh` |
| qwen2.5-coder | 7b o 14b | `ollama pull qwen2.5-coder:14b-instruct-q4_K_M` |
| OpenSCAD | 2021.01+ | `sudo apt install openscad` |
| requests (Python) | — | `pip install requests` |

---

## Generare il Primo Modello

### Via Dashboard (modo facile)

1. Vai su `http://localhost:5000`
2. Clicca **"Genera Modello 3D"**
3. Scrivi la descrizione, es: `cubo 30x30x30mm con foro centrale da 10mm`
4. Scegli qualità e clicca **Genera**
5. Attendi — il modello appare nella sezione **Modelli** quando pronto

### Via Task JSON

Crea un file in `~/panda/tasks/` e il worker lo processa automaticamente:

```bash
cat > ~/panda/tasks/mio_cubo.json << 'EOF'
{
  "id": "mio_cubo",
  "type": "generate_3d",
  "priority": 1,
  "description": "Cubo 30x30x30mm con foro passante centrale da 10mm di diametro",
  "parameters": { "size": 30, "hole_d": 10 },
  "object_type": "simple",
  "quality": "medium"
}
EOF
```

### Via API

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Cubo 30x30x30mm con foro passante da 10mm",
    "object_type": "simple",
    "quality": "medium"
  }'
```

### Via Batch Import

```bash
# Importa tutti gli esempi dalla cartella examples/
python3 ~/panda/scripts/batch_import_3d.py

# Con conferma automatica
python3 ~/panda/scripts/batch_import_3d.py --yes

# Da una directory custom
python3 ~/panda/scripts/batch_import_3d.py --dir ~/miei_task/
```

---

## Formato Task JSON — Campi generate_3d

```jsonc
{
  // OBBLIGATORI
  "id":          "nome_univoco",           // stringa senza spazi
  "type":        "generate_3d",            // tipo task
  "description": "Descrizione dettagliata dell'oggetto da generare",

  // CONSIGLIATI
  "priority":    3,                        // 1=urgente, 10=bassa priorità
  "object_type": "simple",                 // "simple" | "mechanical" | "decorative"
  "quality":     "medium",                 // "fast" | "medium" | "high"

  // PARAMETRI DIMENSIONALI (passati al prompt LLM)
  "parameters": {
    "larghezza_mm": 50,
    "altezza_mm":   30,
    "spessore":     3,
    // qualsiasi chiave numerica o stringa utile alla descrizione
  }
}
```

### Valori quality

| Valore | `$fn` OpenSCAD | Uso consigliato |
|---|---|---|
| `fast` | 32 | Bozze, test rapidi |
| `medium` | 64 | Uso normale (default) |
| `high` | 128 | Stampa finale, dettagli fini |

### Valori object_type

| Valore | Descrizione |
|---|---|
| `simple` | Oggetti geometrici semplici (scatole, supporti, organizer) |
| `mechanical` | Parti meccaniche (viti, dadi, ingranaggi, bracket) |
| `decorative` | Oggetti con curve e forme estetiche |

---

## Script di Utilità

### check_system.py — Diagnostica

```bash
python3 ~/panda/scripts/check_system.py         # report colorato
python3 ~/panda/scripts/check_system.py --fix   # crea cartelle mancanti
python3 ~/panda/scripts/check_system.py --json  # output JSON per automazione
python3 ~/panda/scripts/check_system.py --quiet # solo errori e warning
```

### start_panda3d.sh — Avvio

```bash
bash ~/panda/scripts/start_panda3d.sh            # avvio completo con log tail
bash ~/panda/scripts/start_panda3d.sh --check    # solo verifica, no avvio
bash ~/panda/scripts/start_panda3d.sh --no-tail  # avvio senza tail dei log
```

### batch_import_3d.py — Import Massivo

```bash
python3 ~/panda/scripts/batch_import_3d.py                     # da examples/
python3 ~/panda/scripts/batch_import_3d.py --dir ~/miei_task/  # da altra dir
python3 ~/panda/scripts/batch_import_3d.py --yes               # senza conferma
python3 ~/panda/scripts/batch_import_3d.py --dry-run           # anteprima
python3 ~/panda/scripts/batch_import_3d.py --priority-filter 3 # solo prio ≤ 3
```

### export_models.py — Export ZIP

```bash
python3 ~/panda/scripts/export_models.py                   # crea export_{ts}.zip
python3 ~/panda/scripts/export_models.py --output ~/Desktop/modelli.zip
python3 ~/panda/scripts/export_models.py --include-scad    # include file .scad
python3 ~/panda/scripts/export_models.py --since 2026-02-01
python3 ~/panda/scripts/export_models.py --list            # solo elenco
```

### model_stats.py — Statistiche

```bash
python3 ~/panda/scripts/model_stats.py            # report testuale
python3 ~/panda/scripts/model_stats.py --top 10   # top 10 per dimensione
python3 ~/panda/scripts/model_stats.py --verbose  # dettaglio per modello
python3 ~/panda/scripts/model_stats.py --json     # output JSON raw
```

---

## Esempi Task Pronti

Nella cartella `~/panda/tasks/examples/` trovi:

| File | Oggetto | Tipo |
|---|---|---|
| `supporto_telefono.json` | Supporto scrivania 80×80mm, angolo 70°, slot cavo USB-C | simple |
| `vite_m6.json` | Vite M6×30mm testa esagonale ISO 4017 | mechanical |
| `organizer_cassetto.json` | Organizer 200×100×50mm con 6 scomparti 2×3 | simple |
| `porta_rotolo.json` | Porta carta igienica da parete, staffa a C | simple |
| `dado_m6.json` | Dado M6 esagonale ISO 4032, chiave 10mm | mechanical |
| `batch_cucina.json` | **Batch**: porta spezie (5 slot) + supporto tagliere + porta sacchetti | simple |

Per importarli tutti:

```bash
python3 ~/panda/scripts/batch_import_3d.py --yes
```

---

## Gestione Servizi systemd

```bash
# Stato
sudo systemctl status panda
sudo systemctl status panda-dashboard

# Avvio / Stop / Riavvio
sudo systemctl start   panda panda-dashboard
sudo systemctl stop    panda panda-dashboard
sudo systemctl restart panda panda-dashboard

# Abilita avvio automatico al boot
sudo systemctl enable panda panda-dashboard

# Log in tempo reale
sudo journalctl -u panda          -f
sudo journalctl -u panda-dashboard -f
```

---

## Configurazione — config/panda.json

```json
{
  "ollama_url":      "http://localhost:11434",
  "model":           "qwen2.5-coder:14b-instruct-q4_K_M",
  "model_fallback":  "qwen2.5-coder:7b-instruct-q8_0",
  "check_interval":  15,
  "max_retries":     2,
  "openscad_binary": "openscad",
  "openscad_timeout": 300,
  "default_quality": "medium",
  "quality_presets": {
    "fast":   { "fn": 32,  "detail_level": "low" },
    "medium": { "fn": 64,  "detail_level": "medium" },
    "high":   { "fn": 128, "detail_level": "high" }
  }
}
```

| Campo | Significato |
|---|---|
| `check_interval` | Secondi tra polling della coda task |
| `max_retries` | Tentativi LLM prima di fallire il task |
| `openscad_timeout` | Secondi max per compilazione STL |

---

## Troubleshooting

### LLM troppo lento / timeout

**Sintomo:** il task rimane in elaborazione per minuti o fallisce con timeout.

```bash
# Controlla il modello attivo
ollama list
ollama ps

# Usa il modello più leggero
ollama pull qwen2.5-coder:7b-instruct-q8_0
```

Poi in `config/panda.json` abbassa il modello:
```json
"model": "qwen2.5-coder:7b-instruct-q8_0"
```

Oppure abbassa la qualità nel task JSON: `"quality": "fast"`.

---

### OpenSCAD: errori di compilazione

**Sintomo:** nel result JSON c'è `"success": false` e `compile_log` con errori.

```bash
# Vedi il file SCAD generato
cat ~/panda/models/scad/<nome>.scad

# Compila manualmente per vedere l'errore
openscad --render ~/panda/models/scad/<nome>.scad -o /tmp/test.stl
```

Cause comuni:
- Il LLM ha generato SCAD non valido → riprova con descrizione più semplice
- Versione OpenSCAD vecchia → `sudo apt upgrade openscad`
- Timeout → aumenta `openscad_timeout` in config.json

---

### Modello STL non valido / non stampabile

**Sintomo:** lo STL viene generato ma il slicer mostra errori o geometria non-manifold.

```bash
# Controlla dimensioni
python3 ~/panda/scripts/model_stats.py --verbose

# STL molto piccolo (< 1 KB) = probabilmente vuoto o un punto
ls -lh ~/panda/models/stl/
```

Soluzioni:
- Aggiungi più dettagli alla descrizione (dimensioni esatte, pareti minime 2mm)
- Usa `"quality": "high"` per geometrie complesse
- Specifica esplicitamente nei `parameters` le misure critiche

---

### Worker non elabora i task

**Sintomo:** i file JSON restano in `~/panda/tasks/` senza essere processati.

```bash
# Verifica che il worker sia in esecuzione
pgrep -f worker.py
sudo systemctl status panda

# Controlla i log
tail -f ~/panda/logs/panda-stdout.log
tail -f ~/panda/logs/panda-stderr.log

# Riavvia
sudo systemctl restart panda
```

---

### Dashboard non raggiungibile (porta 5000)

```bash
# Verifica che sia in esecuzione
pgrep -f server.py
sudo systemctl status panda-dashboard

# Controlla che la porta sia in ascolto
ss -tlnp | grep 5000

# Riavvia
sudo systemctl restart panda-dashboard
```

---

### Ollama non disponibile

```bash
# Avvia Ollama
ollama serve &

# Oppure tramite systemd
sudo systemctl start ollama
sudo systemctl enable ollama   # avvio automatico

# Verifica
curl http://localhost:11434/api/tags
```

---

## Struttura Cartelle

```
~/panda/
├── worker.py                    # Worker principale
├── config/
│   └── panda.json               # Configurazione
├── dashboard/
│   └── server.py                # Dashboard Flask (porta 5000)
├── tasks/
│   ├── *.json                   # Task in attesa
│   ├── done/                    # Task completati
│   └── examples/                # Task di esempio pronti
├── models/
│   ├── stl/                     # Modelli STL generati
│   ├── scad/                    # Sorgenti OpenSCAD
│   └── thumbnails/              # Anteprime (se abilitate)
├── results/
│   └── *.json                   # Log di ogni task eseguito
├── logs/
│   ├── YYYY-MM-DD.log           # Log giornalieri
│   ├── panda-stdout.log         # stdout systemd
│   └── panda-stderr.log         # stderr systemd
├── scripts/
│   ├── start_panda3d.sh         # Avvio completo
│   ├── check_system.py          # Diagnostica
│   ├── batch_import_3d.py       # Import batch task
│   ├── export_models.py         # Export ZIP
│   └── model_stats.py           # Statistiche
├── prompts/                     # Template prompt LLM
└── status/
    └── current.json             # Stato live worker
```

---

## API Reference rapida

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/api/status` | Stato worker e sistema |
| GET | `/api/tasks/pending` | Task in attesa |
| GET | `/api/tasks/done` | Task completati |
| POST | `/api/tasks/import` | Importa lista task `{"tasks":[...]}` |
| POST | `/api/generate` | Genera modello rapido |
| GET | `/api/models` | Lista STL disponibili |
| GET | `/api/models/<file>/download` | Scarica STL |
| DELETE | `/api/models/<file>` | Elimina STL |
| GET | `/api/results` | Ultimi result JSON |
