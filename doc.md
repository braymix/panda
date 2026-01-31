# 🐼 PANDA - Documentazione Completa

## Pana Automating Never Death (on) Afterwork

**Versione:** 3.0  
**Data:** Gennaio 2026  
**Autore:** Michele (Pana)

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Architettura](#architettura)
3. [Requisiti di Sistema](#requisiti-di-sistema)
4. [Struttura File e Cartelle](#struttura-file-e-cartelle)
5. [Tipi di Task](#tipi-di-task)
6. [Formato JSON dei Task](#formato-json-dei-task)
7. [API REST](#api-rest)
8. [Configurazione](#configurazione)
9. [Servizi Systemd](#servizi-systemd)
10. [Esempi di Utilizzo](#esempi-di-utilizzo)
11. [Importazione Massiva](#importazione-massiva)
12. [Troubleshooting](#troubleshooting)
13. [Prompt Engineering per LLM](#prompt-engineering-per-llm)

---

## Panoramica

PANDA è un sistema di automazione task basato su LLM locale (Ollama) che gira h24 su hardware dedicato. Permette di:

- Eseguire comandi bash generati da AI
- Generare ed eseguire codice Python
- Creare file con contenuto generato da AI
- Gestire code di task con priorità
- Monitorare tutto via dashboard web

**Stack Tecnologico:**
- **OS:** Linux Mint
- **LLM Engine:** Ollama
- **Modello:** qwen2.5-coder (1.5b / 3b / 7b)
- **Worker:** Python 3
- **Dashboard:** Flask + JavaScript
- **Process Manager:** systemd

---

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                      PANDA System                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Dashboard │    │   Worker    │    │   Ollama    │     │
│  │   (Flask)   │◄──►│  (Python)   │◄──►│   (LLM)     │     │
│  │   :5000     │    │             │    │   :11434    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                               │
│         ▼                  ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  File System                        │   │
│  │  ~/panda/                                           │   │
│  │  ├── tasks/        (coda task JSON)                 │   │
│  │  ├── tasks/done/   (task completati)                │   │
│  │  ├── results/      (risultati JSON)                 │   │
│  │  ├── logs/         (log giornalieri)                │   │
│  │  ├── status/       (stato corrente)                 │   │
│  │  ├── config/       (configurazione)                 │   │
│  │  └── dashboard/    (server web)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Requisiti di Sistema

### Hardware Minimo
- CPU: 4 core
- RAM: 8GB (16GB consigliati)
- Storage: 20GB liberi

### Hardware Consigliato (come installazione attuale)
- CPU: AMD Ryzen 7 5825U (8 core / 16 thread)
- RAM: 16GB
- Storage: 468GB SSD
- GPU: Integrata AMD (non utilizzata per LLM)

### Software
- Linux Mint (o Ubuntu/Debian based)
- Python 3.10+
- Ollama 0.14.0+
- Flask + Flask-SocketIO
- systemd

---

## Struttura File e Cartelle

```
~/panda/
├── worker.py              # Worker principale v3.0
├── config/
│   └── panda.json         # Configurazione (hot reload)
├── tasks/
│   ├── *.json             # Task in coda
│   ├── *_prompt.txt       # Prompt esterni (opzionale)
│   └── done/              # Task completati
├── results/
│   └── *.json             # Risultati esecuzione
├── logs/
│   ├── YYYY-MM-DD.log     # Log giornalieri
│   ├── panda-stdout.log   # Output systemd
│   └── panda-stderr.log   # Errori systemd
├── status/
│   └── current.json       # Stato task corrente
├── scripts/
│   └── temp_*.py          # Script Python temporanei
└── dashboard/
    ├── server.py          # Server Flask
    └── templates/
        └── index.html     # UI Dashboard
```

---

## Tipi di Task

### 1. `prompt`
Invia una domanda generica a Ollama e salva la risposta.

```json
{
  "id": "domanda_esempio",
  "type": "prompt",
  "priority": 10,
  "prompt": "Spiega cos'è il machine learning in 3 frasi"
}
```

**Uso:** Ottenere informazioni, spiegazioni, analisi testuali.

---

### 2. `bash`
PANDA chiede a Ollama di generare un comando bash, poi lo esegue.

```json
{
  "id": "lista_file",
  "type": "bash",
  "priority": 5,
  "prompt": "Elenca tutti i file Python nella cartella corrente"
}
```

**Uso:** Operazioni su file system, comandi di sistema, automazioni.

**Attenzione:** Il comando viene eseguito con i permessi dell'utente PANDA.

---

### 3. `python`
PANDA chiede a Ollama di generare codice Python, poi lo esegue.

```json
{
  "id": "calcolo_esempio",
  "type": "python",
  "priority": 10,
  "prompt": "Scrivi uno script che calcola i primi 20 numeri di Fibonacci e li stampa"
}
```

**Uso:** Calcoli, elaborazione dati, scraping, automazioni complesse.

---

### 4. `file`
PANDA chiede a Ollama di generare contenuto e lo salva in un file specificato.

```json
{
  "id": "crea_readme",
  "type": "file",
  "priority": 10,
  "filepath": "~/panda/progetti/mio_progetto/README.md",
  "prompt": "Crea un README per un progetto Python di web scraping"
}
```

**Uso:** Generare codice, documentazione, configurazioni, template.

**OBBLIGATORIO:** Il campo `filepath` deve essere presente.

---

### 5. `test`
Esegue un comando e verifica se l'output contiene una stringa attesa.

```json
{
  "id": "test_server",
  "type": "test",
  "priority": 10,
  "test_name": "Verifica server attivo",
  "test_command": "curl -s http://localhost:5000/api/status",
  "expected": "panda_running"
}
```

**Uso:** Verifiche automatiche, CI/CD, monitoring.

---

### 6. `multi`
Esegue una sequenza di step in ordine.

```json
{
  "id": "setup_progetto",
  "type": "multi",
  "priority": 1,
  "steps": [
    {"type": "bash", "prompt": "Crea cartella ~/progetti/nuovo"},
    {"type": "file", "filepath": "~/progetti/nuovo/main.py", "prompt": "Crea script hello world"},
    {"type": "bash", "prompt": "Esegui python ~/progetti/nuovo/main.py"}
  ]
}
```

**Uso:** Workflow complessi, setup progetti, pipeline.

---

## Formato JSON dei Task

### Struttura Base

```json
{
  "id": "identificativo_univoco",
  "type": "prompt|bash|python|file|test|multi",
  "priority": 10,
  "prompt": "Descrizione di cosa fare"
}
```

### Campi

| Campo | Tipo | Obbligatorio | Descrizione |
|-------|------|--------------|-------------|
| `id` | string | Sì | Identificativo univoco del task |
| `type` | string | Sì | Tipo di task (vedi sezione Tipi) |
| `priority` | int | No (default: 10) | Priorità esecuzione (1 = prima) |
| `prompt` | string | Sì | Istruzioni per Ollama |
| `filepath` | string | Solo per `file` | Percorso dove salvare il file |
| `prompt_file` | string | No | Path a file .txt con prompt lungo |
| `test_name` | string | Solo per `test` | Nome descrittivo del test |
| `test_command` | string | Solo per `test` | Comando da eseguire |
| `expected` | string | Solo per `test` | Stringa attesa nell'output |
| `steps` | array | Solo per `multi` | Lista di step da eseguire |

### Prompt Esterni

Per prompt molto lunghi, usa file separati:

```json
{
  "id": "task_complesso",
  "type": "file",
  "priority": 5,
  "filepath": "~/output/risultato.py",
  "prompt_file": "task_complesso_prompt.txt"
}
```

Il file `task_complesso_prompt.txt` deve essere nella stessa cartella (`~/panda/tasks/`).

---

## API REST

Base URL: `http://IP_PANDA:5000`

### GET /api/status
Stato del sistema.

**Response:**
```json
{
  "panda_running": true,
  "current_task": {
    "current_task": "nome_task",
    "task_type": "bash",
    "status": "running",
    "progress": "Elaborazione...",
    "updated_at": "2026-01-28T10:30:00"
  }
}
```

---

### GET /api/tasks/pending
Lista task in coda.

**Response:**
```json
[
  {
    "filename": "task_123456_mio_task.json",
    "id": "mio_task",
    "type": "bash",
    "priority": 5,
    "prompt": "Descrizione troncata..."
  }
]
```

---

### GET /api/tasks/done
Lista ultimi 30 task completati.

**Response:**
```json
[
  {
    "filename": "task_completato.json",
    "id": "nome_task",
    "type": "python"
  }
]
```

---

### GET /api/results
Lista ultimi 30 risultati.

**Response:**
```json
[
  {
    "filename": "nome_task_20260128_103000.json",
    "task_id": "nome_task",
    "success": true
  }
]
```

---

### GET /api/logs
Ultime 150 righe del log di oggi.

**Response:**
```json
{
  "lines": [
    "[2026-01-28 10:30:00] [INFO] Task completato",
    "..."
  ]
}
```

---

### POST /api/control/{action}
Controlla il servizio PANDA.

**Actions:** `start`, `stop`, `restart`

**Response:**
```json
{
  "success": true
}
```

---

### POST /api/tasks/add
Aggiunge un singolo task.

**Request Body:**
```json
{
  "id": "nuovo_task",
  "type": "bash",
  "priority": 10,
  "prompt": "Elenca i file"
}
```

**Response:**
```json
{
  "success": true,
  "filename": "task_1706438400_nuovo_task.json"
}
```

---

### POST /api/tasks/import
Importa multipli task.

**Request Body:**
```json
{
  "tasks": [
    {"id": "task1", "type": "bash", "priority": 1, "prompt": "..."},
    {"id": "task2", "type": "python", "priority": 2, "prompt": "..."}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "imported": 2,
  "filenames": ["task_123_task1.json", "task_124_task2.json"]
}
```

---

### DELETE /api/tasks/pending/{filename}
Elimina un task dalla coda.

**Response:**
```json
{
  "success": true
}
```

---

## Configurazione

File: `~/panda/config/panda.json`

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "qwen2.5-coder:7b",
  "check_interval": 10,
  "max_retries": 3,
  "execute_code": true,
  "execute_bash": true,
  "modify_files": true
}
```

### Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `ollama_url` | string | http://localhost:11434 | URL server Ollama |
| `model` | string | qwen2.5-coder:3b | Modello LLM da usare |
| `check_interval` | int | 10 | Secondi tra controlli coda |
| `max_retries` | int | 3 | Tentativi su errore |
| `execute_code` | bool | true | Abilita esecuzione Python |
| `execute_bash` | bool | true | Abilita esecuzione bash |
| `modify_files` | bool | true | Abilita creazione file |

**Hot Reload:** Le modifiche vengono applicate al prossimo ciclo senza riavvio.

### Modelli Disponibili

| Modello | RAM | Velocità | Qualità |
|---------|-----|----------|---------|
| qwen2.5-coder:1.5b | ~4GB | Veloce | Base |
| qwen2.5-coder:3b | ~6GB | Media | Buona |
| qwen2.5-coder:7b | ~10GB | Lenta | Ottima |

---

## Servizi Systemd

### PANDA Worker
```bash
sudo systemctl start panda      # Avvia
sudo systemctl stop panda       # Ferma
sudo systemctl restart panda    # Riavvia
sudo systemctl status panda     # Stato
sudo systemctl enable panda     # Avvio automatico
```

### PANDA Dashboard
```bash
sudo systemctl start panda-dashboard
sudo systemctl stop panda-dashboard
sudo systemctl restart panda-dashboard
sudo systemctl status panda-dashboard
```

### Log in tempo reale
```bash
tail -f ~/panda/logs/*.log
journalctl -u panda -f
journalctl -u panda-dashboard -f
```

---

## Esempi di Utilizzo

### Esempio 1: Hello World Multilingua

```json
{
  "tasks": [
    {
      "id": "crea_cartelle",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea le cartelle ~/panda/progetti/hello/{it,es,fr}"
    },
    {
      "id": "hello_italiano",
      "type": "file",
      "priority": 2,
      "filepath": "~/panda/progetti/hello/it/index.html",
      "prompt": "Crea pagina HTML con Ciao Mondo, sfondo blu, testo bianco"
    },
    {
      "id": "hello_spagnolo",
      "type": "file",
      "priority": 3,
      "filepath": "~/panda/progetti/hello/es/index.html",
      "prompt": "Crea pagina HTML con Hola Mundo, sfondo rosso, testo bianco"
    },
    {
      "id": "hello_francese",
      "type": "file",
      "priority": 4,
      "filepath": "~/panda/progetti/hello/fr/index.html",
      "prompt": "Crea pagina HTML con Bonjour Monde, sfondo verde, testo bianco"
    }
  ]
}
```

---

### Esempio 2: Setup Progetto Python

```json
{
  "tasks": [
    {
      "id": "setup_struttura",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea struttura ~/panda/progetti/myapp con cartelle src, tests, docs"
    },
    {
      "id": "crea_main",
      "type": "file",
      "priority": 2,
      "filepath": "~/panda/progetti/myapp/src/main.py",
      "prompt": "Crea un main.py con una classe App che ha metodi start() e stop() con logging"
    },
    {
      "id": "crea_requirements",
      "type": "file",
      "priority": 3,
      "filepath": "~/panda/progetti/myapp/requirements.txt",
      "prompt": "Crea requirements.txt con requests, flask, python-dotenv"
    },
    {
      "id": "crea_readme",
      "type": "file",
      "priority": 4,
      "filepath": "~/panda/progetti/myapp/README.md",
      "prompt": "Crea README.md professionale per il progetto MyApp"
    },
    {
      "id": "crea_test",
      "type": "file",
      "priority": 5,
      "filepath": "~/panda/progetti/myapp/tests/test_main.py",
      "prompt": "Crea test unitari pytest per la classe App"
    }
  ]
}
```

---

### Esempio 3: Automazione Sistema

```json
{
  "tasks": [
    {
      "id": "backup_config",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea backup compresso della cartella ~/panda/config in ~/backups con data nel nome"
    },
    {
      "id": "check_disk",
      "type": "bash",
      "priority": 2,
      "prompt": "Mostra spazio disco disponibile in formato leggibile"
    },
    {
      "id": "cleanup_temp",
      "type": "bash",
      "priority": 3,
      "prompt": "Elimina file temporanei più vecchi di 7 giorni in ~/panda/scripts"
    }
  ]
}
```

---

### Esempio 4: Generazione Report

```json
{
  "tasks": [
    {
      "id": "analisi_log",
      "type": "python",
      "priority": 1,
      "prompt": "Leggi ~/panda/logs/*.log, conta errori e warning, stampa un riepilogo"
    },
    {
      "id": "report_html",
      "type": "file",
      "priority": 2,
      "filepath": "~/panda/reports/daily_report.html",
      "prompt": "Crea report HTML con statistiche task completati oggi, usa grafici CSS"
    }
  ]
}
```

---

## Importazione Massiva

### Via Dashboard UI
1. Vai a `http://IP:5000`
2. Sezione "📥 Importa Task da JSON"
3. Incolla il JSON
4. Click "Importa Tasks"

### Via cURL
```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"id":"test","type":"bash","priority":1,"prompt":"echo hello"}]}'
```

### Via Script Python
```python
import requests
import json

tasks = {
    "tasks": [
        {"id": "task1", "type": "bash", "priority": 1, "prompt": "ls -la"},
        {"id": "task2", "type": "python", "priority": 2, "prompt": "print(2+2)"}
    ]
}

response = requests.post(
    "http://localhost:5000/api/tasks/import",
    json=tasks
)
print(response.json())
```

### Via File JSON
```bash
# Crea file tasks_to_import.json
cat << 'EOF' > tasks_to_import.json
{
  "tasks": [
    {"id": "task1", "type": "bash", "priority": 1, "prompt": "whoami"}
  ]
}
EOF

# Importa
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d @tasks_to_import.json
```

---

## Troubleshooting

### PANDA non parte
```bash
# Controlla stato
sudo systemctl status panda

# Vedi errori
journalctl -u panda -n 50

# Verifica Ollama
curl http://localhost:11434/api/tags
```

### Dashboard non risponde
```bash
# Controlla stato
sudo systemctl status panda-dashboard

# Testa manualmente
python3 ~/panda/dashboard/server.py

# Verifica porta
ss -tlnp | grep 5000
```

### Task falliscono sempre
```bash
# Controlla risultati
cat ~/panda/results/NOME_TASK_*.json

# Verifica modello
ollama list
ollama run qwen2.5-coder:7b "test"
```

### Ollama lento
```bash
# Controlla risorse
htop

# Usa modello più piccolo
nano ~/panda/config/panda.json
# Cambia model in qwen2.5-coder:3b
```

---

## Prompt Engineering per LLM

### Best Practices

1. **Sii specifico**: "Crea file X con Y" invece di "fai qualcosa"

2. **Un task = un'azione**: Dividi compiti complessi in più task

3. **Specifica il formato**: "Rispondi solo con il codice, senza spiegazioni"

4. **Indica vincoli**: "Massimo 50 righe", "Usa solo librerie standard"

5. **Dai contesto**: "Questo è per un server Linux Mint con Python 3.12"

### Template Prompt Efficaci

**Per bash:**
```
Genera SOLO il comando bash per: [descrizione]
Non aggiungere spiegazioni.
```

**Per Python:**
```
Scrivi uno script Python che:
1. [punto 1]
2. [punto 2]
Solo codice, niente commenti, niente markdown.
```

**Per file:**
```
Crea [tipo file] completo per [scopo].
Includi: [elemento 1], [elemento 2]
Stile: [specifiche]
Non aggiungere spiegazioni, solo il contenuto del file.
```

### Esempi Prompt Ottimizzati

❌ **Male:**
```
"fai un sito web"
```

✅ **Bene:**
```
"Crea una pagina HTML5 con: titolo 'Portfolio', navbar con link Home/About/Contact, sezione hero con h1 e paragrafo, footer con copyright 2026. CSS inline, sfondo scuro #1a1a2e, testo chiaro, font system-ui"
```

---

## Contatti e Supporto

- **Progetto:** PANDA v3.0
- **Autore:** Michele (Pana)
- **Hardware:** Mini PC Linux Mint, Ryzen 7 5825U, 16GB RAM
- **LLM:** Ollama + qwen2.5-coder

---

*Documentazione generata per uso interno e integrazione AI.*
