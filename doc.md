# PANDA - Documentazione Completa e Approfondita

## Pana Automating Never Death (on) Afterwork

**Versione:** 3.1
**Data:** Gennaio 2026
**Autore:** Michele (Pana)
**Sistema Operativo:** Linux Mint

---

## Indice Generale

1. [Introduzione e Filosofia del Progetto](#introduzione-e-filosofia-del-progetto)
2. [Panoramica del Sistema](#panoramica-del-sistema)
3. [Architettura Dettagliata](#architettura-dettagliata)
4. [Requisiti di Sistema](#requisiti-di-sistema)
5. [Installazione e Configurazione Iniziale](#installazione-e-configurazione-iniziale)
6. [Struttura Completa delle Directory](#struttura-completa-delle-directory)
7. [Il Worker: Cuore Pulsante di PANDA](#il-worker-cuore-pulsante-di-panda)
8. [Tipi di Task: Guida Completa](#tipi-di-task-guida-completa)
9. [Formato JSON dei Task: Anatomia Completa](#formato-json-dei-task-anatomia-completa)
10. [API REST: Riferimento Completo](#api-rest-riferimento-completo)
11. [La Dashboard Web](#la-dashboard-web)
12. [Configurazione Avanzata](#configurazione-avanzata)
13. [Integrazione con Ollama e LLM](#integrazione-con-ollama-e-llm)
14. [Servizi Systemd](#servizi-systemd)
15. [Esempi Pratici di Utilizzo](#esempi-pratici-di-utilizzo)
16. [Sistema di Logging](#sistema-di-logging)
17. [Gestione degli Errori e Retry](#gestione-degli-errori-e-retry)
18. [Prompt Engineering: Best Practices](#prompt-engineering-best-practices)
19. [Troubleshooting e Risoluzione Problemi](#troubleshooting-e-risoluzione-problemi)
20. [Sicurezza e Considerazioni](#sicurezza-e-considerazioni)
21. [Appendice: Riferimenti Rapidi](#appendice-riferimenti-rapidi)

---

## Introduzione e Filosofia del Progetto

### Cos'è PANDA?

PANDA, acronimo creativo di "Pana Automating Never Death (on) Afterwork", rappresenta una soluzione innovativa nel panorama dell'automazione intelligente. Si tratta di un sistema di automazione task che sfrutta la potenza dei Large Language Models (LLM) eseguiti localmente attraverso Ollama, progettato per funzionare in modo continuo e autonomo su hardware dedicato.

L'idea fondamentale alla base di PANDA nasce dall'esigenza di avere un "assistente digitale" sempre attivo, capace di eseguire compiti di varia natura senza richiedere supervisione costante. A differenza delle soluzioni cloud-based, PANDA opera interamente in locale, garantendo privacy dei dati, controllo totale sull'infrastruttura e indipendenza da servizi esterni.

### La Filosofia "Never Death"

Il nome stesso riflette la filosofia del progetto: un sistema che "non muore mai", pensato per essere sempre disponibile, resiliente agli errori e capace di auto-ripristinarsi. Quando qualcosa va storto, PANDA non si ferma definitivamente: riprova, logga l'errore e continua a servire le richieste successive.

Questa resilienza si manifesta in diversi modi:
- **Retry automatico** dei task falliti (configurabile fino a N tentativi)
- **Gestione graceful** delle eccezioni senza crash del worker
- **Hot reload** della configurazione senza necessità di riavvio
- **Logging persistente** per debug e analisi post-mortem

### Per Chi è Pensato PANDA?

PANDA è ideale per:
- **Sviluppatori** che vogliono automatizzare task ripetitivi di sviluppo
- **Sistemisti** che necessitano di automazione su server locali
- **Appassionati di AI** che vogliono sperimentare con LLM in modo pratico
- **Piccole aziende** che cercano soluzioni di automazione privacy-friendly
- **Hobbisti** che desiderano un assistente AI personale sempre attivo

---

## Panoramica del Sistema

### Cosa Può Fare PANDA?

PANDA è progettato per gestire una vasta gamma di operazioni automatizzate. Ecco le principali capacità del sistema:

#### 1. Esecuzione Comandi Bash Intelligente

PANDA non si limita a eseguire comandi predefiniti. Quando riceve un task di tipo "bash", interroga l'LLM locale per generare il comando appropriato basandosi su una descrizione in linguaggio naturale. Questo significa che puoi semplicemente dire "elenca tutti i file Python nella cartella corrente" e PANDA genererà ed eseguirà il comando `find . -name "*.py"` o `ls *.py` a seconda del contesto.

#### 2. Generazione ed Esecuzione Codice Python

Similmente ai comandi bash, PANDA può generare codice Python completo a partire da descrizioni testuali. Vuoi uno script che calcoli i numeri di Fibonacci? Basta descriverlo e PANDA lo creerà e lo eseguirà, restituendoti l'output.

#### 3. Creazione File con Contenuto Generato

Una delle funzionalità più potenti è la capacità di generare file completi: codice sorgente, documentazione, configurazioni, template HTML, e molto altro. Specificando il percorso di destinazione e una descrizione del contenuto desiderato, PANDA creerà il file con contenuto generato dall'AI.

#### 4. Test Automatizzati con Validazione

PANDA include un sistema di test integrato che permette di verificare condizioni specifiche. Puoi definire un comando da eseguire e una stringa attesa nell'output: se la stringa è presente, il test passa; altrimenti fallisce. Questo è fondamentale per creare pipeline di CI/CD semplificate o per monitoraggio di servizi.

#### 5. Task Multi-Step Complessi

Per workflow più articolati, PANDA supporta task "multi" che raggruppano più operazioni da eseguire in sequenza. Questo permette di creare vere e proprie pipeline dove ogni step dipende dal precedente.

#### 6. Gestione Code con Priorità

Non tutti i task hanno la stessa urgenza. PANDA implementa un sistema di priorità dove task con valore più basso vengono eseguiti prima. Un task con priorità 1 verrà sempre processato prima di uno con priorità 10.

#### 7. Monitoraggio via Dashboard Web

Una dashboard web moderna e responsive permette di monitorare in tempo reale lo stato del sistema, visualizzare i task in coda, controllare i log e interagire con PANDA senza dover accedere alla riga di comando.

---

## Architettura Dettagliata

### Vista d'Insieme

L'architettura di PANDA segue un design modulare e disaccoppiato, dove ogni componente ha responsabilità ben definite. Questa separazione permette manutenibilità, testabilità e scalabilità del sistema.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PANDA System v3.1                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │    Dashboard    │    │     Worker      │    │     Ollama      │         │
│  │    (Flask)      │◄──►│    (Python)     │◄──►│     (LLM)       │         │
│  │    Porta 5000   │    │    Loop h24     │    │   Porta 11434   │         │
│  │                 │    │                 │    │                 │         │
│  │  - UI Web       │    │  - Processa     │    │  - qwen2.5-     │         │
│  │  - API REST     │    │    task         │    │    coder        │         │
│  │  - Controlli    │    │  - Esegue       │    │  - Genera       │         │
│  │                 │    │    codice       │    │    risposte     │         │
│  └────────┬────────┘    └────────┬────────┘    └─────────────────┘         │
│           │                      │                                          │
│           ▼                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         File System                                   │  │
│  │                                                                       │  │
│  │  ~/panda/                                                             │  │
│  │  ├── tasks/              Coda task da processare (JSON)               │  │
│  │  │   └── done/           Archivio task completati                     │  │
│  │  ├── results/            Output delle esecuzioni (JSON)               │  │
│  │  ├── logs/               Log giornalieri per debug                    │  │
│  │  ├── status/             Stato real-time del worker                   │  │
│  │  ├── config/             Configurazione (hot reload)                  │  │
│  │  ├── scripts/            Script Python temporanei                     │  │
│  │  └── dashboard/          Server web e template                        │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Systemd Services                              │  │
│  │                                                                       │  │
│  │  panda.service           →  Worker principale (always-on)             │  │
│  │  panda-dashboard.service →  Server web dashboard                      │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Componenti Principali

#### Il Worker (worker.py)

Il worker è il cuore pulsante di PANDA. Si tratta di un processo Python che gira continuamente in background, implementando un pattern "polling loop". Ogni N secondi (configurabili, default 10), il worker:

1. **Ricarica la configurazione** dal file JSON (permettendo hot reload)
2. **Scansiona la directory tasks/** alla ricerca di file JSON
3. **Ordina i task** per priorità (valori più bassi = priorità più alta)
4. **Processa ogni task** in sequenza, interfacciandosi con Ollama
5. **Salva i risultati** nella directory results/
6. **Sposta i task completati** nella sottocartella done/
7. **Aggiorna lo stato** nel file status/current.json

Il worker è progettato per essere resiliente: se un task fallisce, può ritentare automaticamente (fino al limite configurato); se si verifica un'eccezione non gestita, il worker la logga e continua a funzionare.

#### La Dashboard (dashboard/server.py)

La dashboard è un'applicazione Flask che fornisce sia un'interfaccia web user-friendly sia un set di API REST per l'integrazione programmatica. Ascolta sulla porta 5000 e offre:

- **Interfaccia grafica** con tema scuro moderno
- **Visualizzazione real-time** dello stato del worker
- **Gestione task** (creazione, eliminazione, import)
- **Visualizzazione log** in tempo reale
- **Controlli di servizio** (start/stop/restart)

La comunicazione tra dashboard e worker avviene indirettamente attraverso il file system: la dashboard scrive task nella cartella tasks/ e legge risultati da results/ e stato da status/.

#### Ollama (Server LLM)

Ollama è il server che ospita ed esegue i modelli LLM localmente. PANDA comunica con Ollama attraverso la sua API REST (default porta 11434). Il modello consigliato è `qwen2.5-coder` nelle varianti:
- **1.5b**: Leggero, veloce, qualità base
- **3b**: Bilanciato, buona qualità
- **7b**: Migliore qualità, richiede più risorse

La scelta del modello dipende dalle risorse hardware disponibili e dal tipo di task da eseguire. Per task di coding complessi, il modello 7b offre risultati significativamente migliori.

### Flusso di Esecuzione di un Task

Per comprendere meglio come funziona PANDA, seguiamo il ciclo di vita completo di un task:

```
1. CREAZIONE
   │
   ├─► Via Dashboard UI (form o import JSON)
   ├─► Via API REST (POST /api/tasks/add o /api/tasks/import)
   └─► Via scrittura diretta file JSON in ~/panda/tasks/

2. CODA
   │
   └─► Il file JSON viene salvato in ~/panda/tasks/
       con nome: task_{timestamp}_{id}.json

3. RILEVAMENTO
   │
   └─► Il worker, nel suo ciclo di polling, trova il file
       e lo aggiunge alla lista ordinata per priorità

4. PROCESSAMENTO
   │
   ├─► Worker aggiorna status/current.json
   ├─► Legge il contenuto del task JSON
   ├─► In base al tipo, prepara il prompt per Ollama
   ├─► Invia richiesta a Ollama API
   ├─► Riceve risposta (codice/comando/contenuto)
   ├─► Pulisce la risposta (rimuove prefazioni LLM)
   └─► Esegue l'azione (bash/python/write file)

5. SALVATAGGIO RISULTATO
   │
   └─► Crea file in ~/panda/results/{id}_{timestamp}.json
       contenente: success, steps, output, eventuali errori

6. ARCHIVIAZIONE
   │
   ├─► Se successo O max_retries raggiunto:
   │   └─► Sposta task in ~/panda/tasks/done/
   │
   └─► Se fallimento E retry disponibili:
       └─► Incrementa _retry nel task e lascia in coda

7. IDLE
   │
   └─► Worker aggiorna status (idle) e attende prossimo ciclo
```

---

## Requisiti di Sistema

### Hardware Minimo

Per eseguire PANDA con prestazioni accettabili, il sistema deve disporre almeno di:

| Componente | Minimo | Note |
|------------|--------|------|
| **CPU** | 4 core | Preferibilmente x64 con AVX2 |
| **RAM** | 8 GB | Per modello 1.5b |
| **Storage** | 20 GB liberi | SSD fortemente consigliato |
| **GPU** | Non richiesta | Ollama usa CPU by default |

### Hardware Consigliato

Per un'esperienza ottimale, specialmente con modelli più grandi:

| Componente | Consigliato | Note |
|------------|-------------|------|
| **CPU** | 8 core / 16 thread | AMD Ryzen 7 o Intel i7 equivalente |
| **RAM** | 16 GB | Permette modello 7b + headroom |
| **Storage** | 50+ GB SSD | NVMe per performance migliori |
| **GPU** | Opzionale | NVIDIA con CUDA per accelerazione |

### Configurazione di Riferimento

L'installazione di riferimento di PANDA gira su:
- **CPU**: AMD Ryzen 7 5825U (8 core / 16 thread)
- **RAM**: 16 GB DDR4
- **Storage**: 468 GB SSD
- **GPU**: AMD integrata (non utilizzata per LLM)
- **OS**: Linux Mint

### Software Richiesto

Prima di installare PANDA, assicurati di avere:

| Software | Versione | Installazione |
|----------|----------|---------------|
| **Python** | 3.10+ | `sudo apt install python3 python3-pip` |
| **Ollama** | 0.14.0+ | Vedi [ollama.ai](https://ollama.ai) |
| **Flask** | 2.0+ | `pip install flask` |
| **Requests** | 2.28+ | `pip install requests` |
| **systemd** | Qualsiasi | Preinstallato su Linux moderni |

### Verifica Prerequisiti

Puoi verificare che tutti i prerequisiti siano soddisfatti con questi comandi:

```bash
# Verifica Python
python3 --version
# Deve mostrare Python 3.10 o superiore

# Verifica Ollama
ollama --version
# Deve mostrare la versione installata

# Verifica che Ollama sia in esecuzione
curl http://localhost:11434/api/tags
# Deve restituire JSON con i modelli disponibili

# Verifica modello disponibile
ollama list
# Deve includere qwen2.5-coder:7b (o la variante scelta)
```

---

## Installazione e Configurazione Iniziale

### Passo 1: Preparazione dell'Ambiente

Prima di tutto, crea la struttura di directory necessaria:

```bash
# Crea la directory principale
mkdir -p ~/panda

# Crea tutte le sottodirectory
mkdir -p ~/panda/{tasks/done,results,logs,status,config,scripts,dashboard/templates}

# Verifica la struttura
tree ~/panda
```

### Passo 2: Installazione Dipendenze Python

Installa le librerie Python necessarie:

```bash
# Installa Flask e requests
pip install flask requests

# Opzionale: Flask-SocketIO per future funzionalità real-time
pip install flask-socketio
```

### Passo 3: Installazione Ollama

Se non hai già Ollama installato:

```bash
# Installa Ollama (Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Avvia il servizio Ollama
systemctl --user start ollama
# oppure
ollama serve &

# Scarica il modello consigliato
ollama pull qwen2.5-coder:7b
# oppure per hardware limitato:
ollama pull qwen2.5-coder:3b
```

### Passo 4: Copia dei File di PANDA

Copia i file principali nelle rispettive posizioni:

```bash
# worker.py → ~/panda/worker.py
# server.py → ~/panda/dashboard/server.py
# index.html → ~/panda/dashboard/templates/index.html
```

### Passo 5: Creazione Configurazione

Crea il file di configurazione iniziale:

```bash
cat > ~/panda/config/panda.json << 'EOF'
{
  "ollama_url": "http://localhost:11434",
  "model": "qwen2.5-coder:7b",
  "check_interval": 10,
  "max_retries": 3,
  "execute_code": true,
  "execute_bash": true,
  "modify_files": true
}
EOF
```

### Passo 6: Test Manuale

Prima di configurare i servizi systemd, verifica che tutto funzioni:

```bash
# Terminale 1: Avvia il worker
python3 ~/panda/worker.py

# Terminale 2: Avvia la dashboard
python3 ~/panda/dashboard/server.py

# Terminale 3: Testa con un task
cat > ~/panda/tasks/test_task.json << 'EOF'
{
  "id": "test_iniziale",
  "type": "bash",
  "priority": 1,
  "prompt": "Mostra la data e ora corrente"
}
EOF

# Osserva il terminale 1 per vedere l'esecuzione
# Verifica il risultato
cat ~/panda/results/test_iniziale_*.json
```

### Passo 7: Configurazione Servizi Systemd

Per un'esecuzione automatica e persistente, configura i servizi systemd. Vedi la sezione dedicata [Servizi Systemd](#servizi-systemd) per i dettagli completi.

---

## Struttura Completa delle Directory

Comprendere la struttura delle directory è fondamentale per lavorare efficacemente con PANDA. Ogni cartella ha uno scopo specifico e segue convenzioni precise.

### Panoramica

```
~/panda/
│
├── worker.py                    # Script principale del worker (v3.1)
├── panda_setup.sh              # Script di setup iniziale (opzionale)
├── doc.md                      # Questa documentazione
│
├── config/
│   └── panda.json              # Configurazione centrale (hot reload)
│
├── tasks/
│   ├── *.json                  # Task in attesa di esecuzione
│   ├── *_prompt.txt            # File prompt esterni (opzionale)
│   └── done/
│       └── *.json              # Task completati (archivio)
│
├── results/
│   └── *.json                  # Risultati delle esecuzioni
│
├── logs/
│   ├── YYYY-MM-DD.log         # Log giornalieri del worker
│   ├── panda-stdout.log       # Output systemd (se configurato)
│   └── panda-stderr.log       # Errori systemd (se configurato)
│
├── status/
│   └── current.json           # Stato real-time del worker
│
├── scripts/
│   └── temp_*.py              # Script Python temporanei generati
│
└── dashboard/
    ├── server.py              # Server Flask per API e UI
    └── templates/
        └── index.html         # Template della dashboard
```

### Dettaglio Directory

#### ~/panda/config/

Questa directory contiene la configurazione centrale di PANDA. Il file `panda.json` viene letto dal worker ad ogni ciclo, permettendo modifiche "a caldo" senza riavvio.

**File: panda.json**
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

Ogni parametro è spiegato in dettaglio nella sezione [Configurazione Avanzata](#configurazione-avanzata).

#### ~/panda/tasks/

La directory `tasks/` è la "inbox" di PANDA. Ogni file JSON qui presente rappresenta un task da eseguire. Il worker scansiona questa directory ad ogni ciclo.

**Convenzione nomi file:**
- `task_{timestamp}_{id}.json` - Creati via API
- `{nome_qualsiasi}.json` - Creati manualmente

**Importante:** I file che iniziano con `_` (underscore) vengono ignorati. Questo permette di "disabilitare" temporaneamente un task rinominandolo `_task.json`.

La sottodirectory `done/` contiene l'archivio dei task completati. I file vengono spostati qui (non copiati) dopo l'esecuzione, mantenendo lo stesso nome.

#### ~/panda/results/

Ogni esecuzione di task produce un file di risultato in questa directory. Il nome segue il pattern `{task_id}_{timestamp}.json`.

**Struttura tipica di un risultato:**
```json
{
  "task_id": "nome_task",
  "type": "bash",
  "success": true,
  "steps": [
    {
      "cmd": "date",
      "result": {
        "success": true,
        "stdout": "Sat Jan 25 10:30:00 CET 2026",
        "stderr": ""
      }
    }
  ]
}
```

#### ~/panda/logs/

I log sono organizzati per data, con un file per ogni giorno nel formato `YYYY-MM-DD.log`. Questo facilita la rotazione automatica e la ricerca di eventi storici.

**Formato log:**
```
[2026-01-25 10:30:00] [INFO] 🐼 PANDA Worker v3.1 avviato
[2026-01-25 10:30:10] [INFO] ▶ Task test_task
[2026-01-25 10:30:15] [INFO] ✅ Task test_task
```

I livelli di log disponibili sono: `INFO`, `WARN`, `ERROR`.

#### ~/panda/status/

Contiene un singolo file `current.json` che rappresenta lo stato istantaneo del worker. Viene aggiornato in tempo reale durante l'esecuzione dei task.

**Struttura:**
```json
{
  "current_task": "nome_task",
  "task_type": "bash",
  "status": "running",
  "progress": "Elaborazione...",
  "updated_at": "2026-01-25T10:30:15.123456"
}
```

Quando il worker è inattivo, `current_task` è `null` e `status` è `"idle"`.

#### ~/panda/scripts/

Directory di lavoro per gli script Python temporanei. Quando PANDA esegue un task di tipo `python`, genera uno script temporaneo qui prima di eseguirlo.

**Convenzione nomi:** `temp_{timestamp}.py`

Questi file vengono mantenuti per debugging; puoi eliminarli periodicamente con:
```bash
find ~/panda/scripts -name "temp_*.py" -mtime +7 -delete
```

#### ~/panda/dashboard/

Contiene il server web e i template HTML:
- `server.py`: Applicazione Flask con tutte le API REST
- `templates/index.html`: Interfaccia utente della dashboard

---

## Il Worker: Cuore Pulsante di PANDA

### Panoramica del Worker

Il file `worker.py` è il componente centrale di PANDA. Con le sue circa 360 righe di codice Python, implementa tutta la logica di orchestrazione dei task. Esaminiamo in dettaglio ogni sezione.

### Costanti e Path

```python
PANDA_HOME = Path.home() / "panda"
TASKS_DIR = PANDA_HOME / "tasks"
RESULTS_DIR = PANDA_HOME / "results"
LOGS_DIR = PANDA_HOME / "logs"
STATUS_DIR = PANDA_HOME / "status"
CONFIG_FILE = PANDA_HOME / "config" / "panda.json"
CURRENT_STATUS_FILE = STATUS_DIR / "current.json"
```

Tutte le path sono relative alla home dell'utente, rendendo PANDA portabile tra sistemi diversi.

### Configurazione di Default

```python
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
```

Se il file `panda.json` non esiste o manca qualche chiave, vengono usati questi valori di default.

### Funzione di Logging

```python
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    # Scrive anche su file giornaliero
```

Il logging è duplice: sia su stdout (visibile in console o nei log systemd) sia su file giornaliero. Il `flush=True` garantisce che i messaggi appaiano immediatamente.

### Comunicazione con Ollama

```python
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
```

La funzione `ask_ollama` invia il prompt all'API di Ollama e attende la risposta completa. Il timeout di 900 secondi (15 minuti) permette risposte lunghe o modelli lenti.

**Importante:** Lo `stream: False` significa che attendiamo la risposta completa, non il token-by-token streaming.

### Pulizia Output LLM

Una delle sfide nell'usare LLM per generare codice è che spesso "parlano troppo". La funzione `clean_llm()` rimuove:

1. **Prefazioni** come "Ecco il codice:", "Here is the code:", "Certamente!"
2. **Blocchi markdown** con \`\`\`language
3. **Nome linguaggio** se appare da solo sulla prima riga

Questo garantisce che l'output sia codice puro, eseguibile senza modifiche.

### Funzioni di Esecuzione

#### exec_bash(cmd)
```python
def exec_bash(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return {"success": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}
```

Esegue comandi shell con timeout di 5 minuti. Restituisce un dizionario con:
- `success`: True se returncode == 0
- `stdout`: Output standard
- `stderr`: Output errori

#### exec_python(code)
```python
def exec_python(code):
    temp = PANDA_HOME / "scripts" / f"temp_{int(time.time())}.py"
    temp.write_text(code)
    p = subprocess.run([sys.executable, str(temp)], ...)
    return {"success": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}
```

Salva il codice in un file temporaneo e lo esegue con l'interprete Python corrente. Questo approccio permette:
- Debugging facile (lo script rimane su disco)
- Isolamento (ogni esecuzione in processo separato)
- Cattura completa di stdout/stderr

#### write_file(path, content)
```python
def write_file(path, content):
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return {"success": True}
```

Crea directory parent se necessario e scrive il contenuto. L'`expanduser()` permette path con `~`.

### Il Loop Principale

```python
def main():
    log("🐼 PANDA Worker v3.1 avviato")
    save_default_config()
    update_status()

    while True:
        try:
            config = load_config()  # Hot reload
            pending = get_pending()  # Task ordinati per priorità

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
```

Caratteristiche chiave:
- **Hot reload**: La config viene riletta ad ogni ciclo
- **Graceful shutdown**: Ctrl+C termina pulitamente
- **Resilienza**: Eccezioni non bloccano il worker
- **Stop condizionale**: Task possono fermare la pipeline

---

## Tipi di Task: Guida Completa

PANDA supporta sei tipi di task, ognuno con caratteristiche e casi d'uso specifici. Comprendere le differenze è fondamentale per sfruttare al meglio il sistema.

### Tipo: prompt

Il tipo `prompt` è il più semplice: invia una domanda all'LLM e salva la risposta testuale nel risultato. Non esegue alcun codice.

**Quando usarlo:**
- Ottenere spiegazioni o informazioni
- Generare testo (articoli, descrizioni, etc.)
- Analisi testuali
- Brainstorming e ideazione

**Esempio:**
```json
{
  "id": "spiega_docker",
  "type": "prompt",
  "priority": 10,
  "prompt": "Spiega Docker in modo semplice, massimo 5 frasi. Concentrati sui concetti chiave: container, immagini, e differenza con le VM."
}
```

**Risultato tipico:**
```json
{
  "task_id": "spiega_docker",
  "type": "prompt",
  "success": true,
  "steps": [
    {
      "response": "Docker è una piattaforma che permette di eseguire applicazioni in ambienti isolati chiamati container. Un container è un'unità leggera che include tutto il necessario per eseguire un'applicazione: codice, librerie e configurazioni. Le immagini Docker sono i template da cui si creano i container, simili a snapshot. A differenza delle macchine virtuali, i container condividono il kernel del sistema operativo host, rendendoli molto più leggeri e veloci da avviare. Questo approccio garantisce che l'applicazione funzioni allo stesso modo ovunque venga eseguita."
    }
  ]
}
```

### Tipo: bash

Il tipo `bash` chiede all'LLM di generare un comando shell, poi lo esegue. È fondamentale per operazioni sul file system e automazione di sistema.

**Quando usarlo:**
- Operazioni su file e directory
- Comandi di sistema (gestione servizi, utenti, etc.)
- Installazione pacchetti
- Backup e maintenance
- Interrogazione dello stato del sistema

**Esempio:**
```json
{
  "id": "backup_config",
  "type": "bash",
  "priority": 1,
  "prompt": "Crea un backup compresso della cartella ~/panda/config nella cartella ~/backups includendo la data nel nome del file"
}
```

**Cosa succede internamente:**
1. PANDA invia a Ollama: "RISPONDI SOLO CON IL COMANDO... Genera il comando bash per: [prompt]"
2. Ollama risponde (es): "tar czf ~/backups/config_backup_$(date +%Y%m%d).tar.gz ~/panda/config"
3. PANDA pulisce la risposta e prende solo la prima riga
4. Esegue il comando con `subprocess.run()`
5. Salva stdout, stderr e exit code nel risultato

**Attenzione alla Sicurezza:**
Il comando viene eseguito con i permessi dell'utente che esegue il worker. Evita prompt che potrebbero generare comandi distruttivi. PANDA non ha protezioni contro `rm -rf /` se l'LLM dovesse generarlo.

### Tipo: python

Il tipo `python` genera ed esegue codice Python. Ideale per elaborazioni dati, calcoli, e logiche complesse che un comando bash non può gestire.

**Quando usarlo:**
- Elaborazione e trasformazione dati
- Calcoli matematici complessi
- Web scraping
- Manipolazione file strutturati (JSON, CSV, XML)
- Interazione con API esterne
- Automazioni che richiedono logica condizionale

**Esempio:**
```json
{
  "id": "analizza_log",
  "type": "python",
  "priority": 5,
  "prompt": "Leggi tutti i file .log in ~/panda/logs, conta quante righe contengono ERROR e quante WARNING, poi stampa un riepilogo formattato"
}
```

**Codice generato (esempio):**
```python
from pathlib import Path

logs_dir = Path.home() / "panda" / "logs"
errors = 0
warnings = 0

for log_file in logs_dir.glob("*.log"):
    content = log_file.read_text()
    errors += content.count("[ERROR]")
    warnings += content.count("[WARN]")

print(f"=== Riepilogo Log ===")
print(f"Errori totali: {errors}")
print(f"Warning totali: {warnings}")
```

**Risultato:**
```json
{
  "task_id": "analizza_log",
  "type": "python",
  "success": true,
  "steps": [
    {
      "code": "...",
      "result": {
        "success": true,
        "stdout": "=== Riepilogo Log ===\nErrori totali: 5\nWarning totali: 23\n",
        "stderr": ""
      }
    }
  ]
}
```

### Tipo: file

Il tipo `file` genera contenuto e lo salva in un percorso specificato. È il tipo più usato per generare codice, documentazione, configurazioni.

**Quando usarlo:**
- Generare codice sorgente
- Creare file di configurazione
- Generare documentazione
- Creare template HTML/CSS
- Generare script di automazione
- Creare file dati (JSON, YAML, etc.)

**Campo obbligatorio:** `filepath` - deve specificare dove salvare il file.

**Esempio:**
```json
{
  "id": "crea_script_backup",
  "type": "file",
  "priority": 10,
  "filepath": "~/panda/scripts/daily_backup.sh",
  "prompt": "Crea uno script bash che: 1) Crea backup di ~/panda/config in ~/backups, 2) Elimina backup più vecchi di 30 giorni, 3) Logga le operazioni con timestamp. Aggiungi commenti esplicativi."
}
```

**File generato (~/panda/scripts/daily_backup.sh):**
```bash
#!/bin/bash
# Daily backup script for PANDA configuration
# Generated by PANDA

BACKUP_DIR="$HOME/backups"
SOURCE_DIR="$HOME/panda/config"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup.log"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Create backup
echo "[$(date)] Starting backup..." >> "$LOG_FILE"
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" "$SOURCE_DIR"
echo "[$(date)] Backup created: config_$DATE.tar.gz" >> "$LOG_FILE"

# Cleanup old backups (older than 30 days)
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
echo "[$(date)] Old backups cleaned up" >> "$LOG_FILE"
```

### Tipo: test

Il tipo `test` esegue un comando e verifica che l'output contenga una stringa attesa. Fondamentale per validazione, monitoring e CI/CD.

**Quando usarlo:**
- Verificare che un servizio sia attivo
- Validare output di script
- Controlli di integrità
- Gate di qualità nelle pipeline
- Monitoring automatizzato

**Campi specifici:**
- `test_name`: Nome descrittivo del test
- `test_command`: Comando da eseguire
- `expected`: Stringa che deve essere presente nell'output

**Esempio:**
```json
{
  "id": "test_panda_running",
  "type": "test",
  "priority": 1,
  "test_name": "Verifica PANDA Worker attivo",
  "test_command": "systemctl is-active panda",
  "expected": "active"
}
```

**Logica di valutazione:**
1. Esegue `test_command`
2. Se `expected` è specificato: verifica che stdout contenga la stringa
3. Se `expected` è vuoto: considera il test passato se exit code == 0

**Comportamento speciale:**
Con `stop_on_test_fail: true` nella config, un test fallito ferma l'intera pipeline. Questo permette di usare i test come "gate" in workflow multi-step.

### Tipo: multi

Il tipo `multi` permette di definire una sequenza di step da eseguire in ordine. Ogni step è a sua volta un mini-task (senza id proprio).

**Quando usarlo:**
- Setup di progetti complessi
- Pipeline di build
- Workflow con dipendenze sequenziali
- Automazioni multi-fase

**Esempio:**
```json
{
  "id": "setup_webapp",
  "type": "multi",
  "priority": 1,
  "steps": [
    {
      "type": "bash",
      "prompt": "Crea la struttura di directory ~/progetti/webapp con cartelle: src, public, tests, config"
    },
    {
      "type": "file",
      "filepath": "~/progetti/webapp/src/index.js",
      "prompt": "Crea un file JavaScript che esporta una funzione 'greet' che accetta un nome e ritorna un saluto"
    },
    {
      "type": "file",
      "filepath": "~/progetti/webapp/tests/index.test.js",
      "prompt": "Crea test Jest per la funzione greet del file src/index.js"
    },
    {
      "type": "file",
      "filepath": "~/progetti/webapp/package.json",
      "prompt": "Crea package.json con nome 'webapp', scripts per test con jest, e dipendenze necessarie"
    },
    {
      "type": "bash",
      "prompt": "Entra in ~/progetti/webapp e esegui npm install"
    },
    {
      "type": "test",
      "test_name": "Verifica test passano",
      "test_command": "cd ~/progetti/webapp && npm test",
      "expected": "PASS"
    }
  ]
}
```

**Esecuzione:**
Gli step vengono eseguiti in ordine. Se uno step fallisce E ha `stop_on_fail: true`, la pipeline si ferma. Altrimenti continua con lo step successivo.

---

## Formato JSON dei Task: Anatomia Completa

### Struttura Base

Ogni task PANDA è un oggetto JSON con almeno questi campi:

```json
{
  "id": "identificativo_univoco",
  "type": "prompt|bash|python|file|test|multi",
  "prompt": "Descrizione di cosa fare"
}
```

### Tutti i Campi Disponibili

| Campo | Tipo | Obbligatorio | Default | Descrizione |
|-------|------|--------------|---------|-------------|
| `id` | string | Sì | - | Identificativo univoco del task. Usato nei log e nei nomi file risultato |
| `type` | string | Sì | - | Uno tra: prompt, bash, python, file, test, multi |
| `priority` | integer | No | 10 | Priorità esecuzione. Valori più bassi = esecuzione prima |
| `prompt` | string | Sì* | - | Istruzioni per l'LLM. *Non richiesto per type=test |
| `prompt_file` | string | No | - | Path a file .txt con prompt lungo. Alternativa a prompt inline |
| `filepath` | string | Solo file | - | Percorso dove salvare il file generato |
| `test_name` | string | Solo test | - | Nome descrittivo del test |
| `test_command` | string | Solo test | - | Comando da eseguire per il test |
| `expected` | string | Solo test | - | Stringa attesa nell'output |
| `steps` | array | Solo multi | - | Lista di step da eseguire in sequenza |
| `stop_on_fail` | boolean | No | false | Se true, ferma la pipeline in caso di fallimento |
| `_retry` | integer | Sistema | 0 | Contatore interno dei retry. Non impostare manualmente |

### Convenzione ID

L'ID del task dovrebbe essere:
- **Univoco** nel contesto della sessione
- **Descrittivo** del task
- **Snake_case** per leggibilità
- **Senza spazi** o caratteri speciali

Esempi validi: `backup_daily`, `test_api_v2`, `genera_report_vendite`

### Gestione Prompt Lunghi

Per prompt molto lunghi, puoi usare un file esterno:

```json
{
  "id": "task_complesso",
  "type": "file",
  "filepath": "~/output/risultato.py",
  "prompt_file": "task_complesso_prompt.txt"
}
```

Il file `task_complesso_prompt.txt` deve essere nella stessa directory del task (~/panda/tasks/).

### Validazione

PANDA non esegue validazione rigorosa del JSON. Se mancano campi obbligatori, il task potrebbe fallire durante l'esecuzione. È buona pratica validare i JSON prima dell'import, specialmente per import massivi.

---

## API REST: Riferimento Completo

La dashboard espone un set completo di API REST per l'integrazione programmatica. Tutte le API rispondono in JSON.

### Base URL

```
http://{IP_PANDA}:5000
```

In locale: `http://localhost:5000`

### Endpoint: Stato Sistema

#### GET /api/status

Restituisce lo stato corrente del sistema PANDA.

**Request:**
```bash
curl http://localhost:5000/api/status
```

**Response:**
```json
{
  "panda_running": true,
  "current_task": {
    "current_task": "backup_daily",
    "task_type": "bash",
    "status": "running",
    "progress": "Elaborazione...",
    "updated_at": "2026-01-25T10:30:00.123456"
  }
}
```

**Campi:**
- `panda_running`: boolean - Se il servizio systemd è attivo
- `current_task`: object|null - Stato del task in esecuzione, o null se idle

---

### Endpoint: Gestione Task

#### GET /api/tasks/pending

Lista dei task in coda, ordinati per priorità.

**Request:**
```bash
curl http://localhost:5000/api/tasks/pending
```

**Response:**
```json
[
  {
    "filename": "task_1706177400_backup_daily.json",
    "id": "backup_daily",
    "type": "bash",
    "priority": 1,
    "prompt": "Esegui backup della configurazione..."
  },
  {
    "filename": "task_1706177500_genera_report.json",
    "id": "genera_report",
    "type": "python",
    "priority": 10,
    "prompt": "Genera report delle vendite..."
  }
]
```

**Note:**
- Il prompt è troncato a 80 caratteri
- L'ordine riflette la priorità di esecuzione

---

#### GET /api/tasks/done

Lista degli ultimi 30 task completati.

**Request:**
```bash
curl http://localhost:5000/api/tasks/done
```

**Response:**
```json
[
  {
    "filename": "task_1706170000_init.json",
    "id": "init",
    "type": "bash"
  }
]
```

---

#### POST /api/tasks/add

Aggiunge un singolo task alla coda.

**Request:**
```bash
curl -X POST http://localhost:5000/api/tasks/add \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_echo",
    "type": "bash",
    "priority": 5,
    "prompt": "Stampa Hello World"
  }'
```

**Body Parameters:**
| Campo | Obbligatorio | Descrizione |
|-------|--------------|-------------|
| id | No | Se omesso, generato come task_{timestamp} |
| type | No | Default: "prompt" |
| priority | No | Default: 10 |
| prompt | Sì | Le istruzioni |
| filepath | Per type=file | Dove salvare |

**Response:**
```json
{
  "success": true,
  "filename": "task_1706177600_test_echo.json"
}
```

---

#### POST /api/tasks/import

Importa multipli task in una singola chiamata.

**Request:**
```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"id": "task1", "type": "bash", "priority": 1, "prompt": "echo uno"},
      {"id": "task2", "type": "bash", "priority": 2, "prompt": "echo due"},
      {"id": "task3", "type": "python", "priority": 3, "prompt": "print(1+2)"}
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "imported": 3,
  "filenames": [
    "task_1706177700_task1.json",
    "task_1706177700_task2.json",
    "task_1706177700_task3.json"
  ]
}
```

**Note Importanti:**
- C'è un delay di 10ms tra ogni task per evitare collisioni di timestamp
- I task vengono creati nell'ordine specificato
- Non c'è validazione del contenuto: task malformati falliranno all'esecuzione

Per una guida completa sull'import massivo, vedi il documento dedicato: [GUIDA_IMPORT_MASSIVO.md](GUIDA_IMPORT_MASSIVO.md)

---

#### DELETE /api/tasks/pending/{filename}

Elimina un task dalla coda prima che venga eseguito.

**Request:**
```bash
curl -X DELETE http://localhost:5000/api/tasks/pending/task_1706177600_test_echo.json
```

**Response:**
```json
{
  "success": true
}
```

**Note:**
- Il filename deve essere esatto (inclusa estensione .json)
- Se il file non esiste, ritorna comunque success: true

---

### Endpoint: Risultati

#### GET /api/results

Lista degli ultimi 30 risultati di esecuzione.

**Request:**
```bash
curl http://localhost:5000/api/results
```

**Response:**
```json
[
  {
    "filename": "test_echo_1706177650.json",
    "task_id": "test_echo",
    "success": true
  },
  {
    "filename": "backup_1706177000.json",
    "task_id": "backup",
    "success": false
  }
]
```

---

### Endpoint: Log

#### GET /api/logs

Restituisce le ultime 150 righe del log di oggi.

**Request:**
```bash
curl http://localhost:5000/api/logs
```

**Response:**
```json
{
  "lines": [
    "[2026-01-25 10:30:00] [INFO] 🐼 PANDA Worker v3.1 avviato",
    "[2026-01-25 10:30:10] [INFO] ▶ Task test_echo",
    "[2026-01-25 10:30:12] [INFO] ✅ Task test_echo"
  ]
}
```

---

### Endpoint: Controllo Servizio

#### POST /api/control/{action}

Controlla il servizio PANDA via systemctl.

**Actions disponibili:** `start`, `stop`, `restart`

**Request:**
```bash
# Avvia
curl -X POST http://localhost:5000/api/control/start

# Ferma
curl -X POST http://localhost:5000/api/control/stop

# Riavvia
curl -X POST http://localhost:5000/api/control/restart
```

**Response:**
```json
{
  "success": true
}
```

**Note:**
- Richiede che l'utente abbia permessi sudo senza password per systemctl
- Utile per riavvii da remoto senza accesso SSH

---

## La Dashboard Web

### Panoramica

La dashboard web è l'interfaccia principale per interagire con PANDA senza usare la linea di comando. Accessibile via browser all'indirizzo `http://IP:5000`, offre una visione completa e controlli intuitivi.

### Caratteristiche Visive

La dashboard presenta un design moderno con:
- **Tema scuro** (#0f0f1a) facile per gli occhi
- **Layout responsive** che si adatta a diverse dimensioni schermo
- **Indicatori colorati** per stato (verde=attivo, rosso=fermo)
- **Aggiornamento automatico** ogni 2-5 secondi

### Sezioni della Dashboard

#### 1. Header e Stato

In cima alla pagina trovi:
- Logo PANDA con titolo
- Badge di stato con indicatore colorato
- Tre pulsanti di controllo: Avvia, Ferma, Riavvia

Il badge mostra "PANDA Attivo" con pallino verde quando il servizio è running, "PANDA Fermo" con pallino rosso altrimenti.

#### 2. Task Corrente

Un riquadro evidenziato mostra il task in esecuzione:
- Nome e tipo del task
- Stato di avanzamento
- Quando idle, mostra "Nessuno - In attesa"

#### 3. Coda Task

Lista dei task in attesa con:
- Priorità (badge giallo)
- ID del task
- Tipo (badge grigio)
- Prompt troncato
- Pulsante X per eliminare

#### 4. Form Creazione Task

Permette di creare nuovi task senza scrivere JSON:
- Campo ID task
- Selettore priorità (1-99)
- Dropdown tipo (prompt, bash, python, file)
- Campo filepath (visibile solo per tipo=file)
- Area prompt multilinea
- Pulsante "Aggiungi alla Coda"

#### 5. Import JSON

Area per import massivo:
- Textarea per incollare JSON
- Guida formato integrata
- Pulsante "Importa Tasks"

#### 6. Task Completati

Lista degli ultimi 20 task completati con ID e tipo.

#### 7. Log Real-time

Box con sfondo nero che mostra le ultime 150 righe di log in tempo reale, con scroll automatico verso il basso.

### Polling e Aggiornamento

La dashboard usa JavaScript per aggiornare i dati periodicamente:
- Stato sistema: ogni 2 secondi
- Coda task: ogni 3 secondi
- Task completati: ogni 5 secondi
- Log: ogni 2 secondi

Questo approccio "polling" è semplice e robusto, anche se meno efficiente di WebSocket.

---

## Configurazione Avanzata

### File di Configurazione

Il file `~/panda/config/panda.json` controlla il comportamento del worker. Viene riletto ad ogni ciclo, permettendo modifiche senza riavvio.

### Parametri Disponibili

#### ollama_url
```json
"ollama_url": "http://localhost:11434"
```

URL del server Ollama. Modifica se:
- Ollama gira su porta diversa
- Ollama è su macchina remota: `"http://192.168.1.100:11434"`
- Usi un proxy

#### model
```json
"model": "qwen2.5-coder:7b"
```

Nome del modello Ollama da usare. Opzioni comuni:
- `qwen2.5-coder:1.5b` - Veloce, ~4GB RAM
- `qwen2.5-coder:3b` - Bilanciato, ~6GB RAM
- `qwen2.5-coder:7b` - Qualità massima, ~10GB RAM

Puoi usare qualsiasi modello installato in Ollama. Verifica con `ollama list`.

#### check_interval
```json
"check_interval": 10
```

Secondi tra ogni ciclo di polling. Valori più bassi = risposta più rapida ma più uso CPU. Consigliato: 5-30.

#### max_retries
```json
"max_retries": 3
```

Numero massimo di tentativi per task falliti. Dopo questo limite, il task viene comunque spostato in done/ (con success=false).

#### execute_bash
```json
"execute_bash": true
```

Abilita/disabilita l'esecuzione di comandi bash. Se false, i task di tipo bash genereranno il comando ma non lo eseguiranno.

#### execute_code
```json
"execute_code": true
```

Abilita/disabilita l'esecuzione di codice Python. Se false, il codice viene generato ma non eseguito.

#### modify_files
```json
"modify_files": true
```

Abilita/disabilita la creazione/modifica di file. Se false, i task di tipo file genereranno contenuto ma non scriveranno su disco.

#### stop_on_test_fail
```json
"stop_on_test_fail": false
```

Se true, un test fallito ferma l'intera pipeline. Utile per workflow dove ogni step dipende dal precedente.

### Esempio Configurazione Conservativa

Per un ambiente dove vuoi più controllo:

```json
{
  "ollama_url": "http://localhost:11434",
  "model": "qwen2.5-coder:3b",
  "check_interval": 30,
  "max_retries": 1,
  "execute_code": false,
  "execute_bash": false,
  "modify_files": true,
  "stop_on_test_fail": true
}
```

Questa configurazione:
- Usa modello più leggero
- Controlla ogni 30 secondi (meno carico)
- Non riprova task falliti
- Non esegue codice (solo genera)
- Permette creazione file
- Ferma pipeline su test falliti

---

## Integrazione con Ollama e LLM

### Come PANDA Comunica con Ollama

La comunicazione avviene tramite API REST. Per ogni task che richiede generazione, PANDA:

1. Costruisce un prompt con istruzioni specifiche
2. Invia POST a `/api/generate` con model e prompt
3. Attende risposta completa (non streaming)
4. Pulisce l'output da prefazioni e markdown

### Endpoint Ollama Usato

```
POST http://localhost:11434/api/generate
Content-Type: application/json

{
  "model": "qwen2.5-coder:7b",
  "prompt": "RISPONDI SOLO CON IL CODICE...",
  "stream": false
}
```

### Timeout e Limiti

- **Timeout richiesta**: 900 secondi (15 minuti)
- **Nessun limite** su lunghezza risposta
- **Nessun retry** automatico su errori Ollama

Se Ollama non risponde entro 15 minuti, il task fallisce.

### Prompt Templates Interni

PANDA usa prompt specifici per ogni tipo di task:

**Per bash:**
```
RISPONDI SOLO CON IL COMANDO, NIENTE ALTRO.
NO introduzioni, NO spiegazioni, NO commenti, NO markdown.
Genera il comando bash per:
{prompt_utente}
```

**Per python:**
```
RISPONDI SOLO CON IL CODICE, NIENTE ALTRO.
NO introduzioni, NO spiegazioni, NO markdown ```.
Scrivi il codice python per:
{prompt_utente}
```

**Per file:**
```
RISPONDI SOLO CON IL CONTENUTO DEL FILE, NIENTE ALTRO.
NO introduzioni come 'Ecco', 'Certamente', 'Here is'.
NO spiegazioni finali, NO markdown ```.
{prompt_utente}
```

### Scelta del Modello

| Modello | Caso d'Uso | Pro | Contro |
|---------|------------|-----|--------|
| 1.5b | Task semplici, testing | Veloce, poca RAM | Qualità limitata |
| 3b | Uso quotidiano | Buon bilanciamento | - |
| 7b | Task complessi, coding | Migliore qualità | Lento, RAM elevata |

**Consiglio:** Inizia con 3b. Passa a 7b se noti output di bassa qualità su task di coding.

---

## Servizi Systemd

### Perché Systemd?

Systemd garantisce che PANDA:
- Si avvii automaticamente al boot
- Si riavvii automaticamente se crasha
- Sia controllabile con comandi standard
- Abbia log integrati con journalctl

### Configurazione PANDA Worker

Crea il file `/etc/systemd/system/panda.service`:

```ini
[Unit]
Description=PANDA Worker - AI Task Automation
After=network.target ollama.service

[Service]
Type=simple
User=TUO_USERNAME
WorkingDirectory=/home/TUO_USERNAME/panda
ExecStart=/usr/bin/python3 /home/TUO_USERNAME/panda/worker.py
Restart=always
RestartSec=10
StandardOutput=append:/home/TUO_USERNAME/panda/logs/panda-stdout.log
StandardError=append:/home/TUO_USERNAME/panda/logs/panda-stderr.log

[Install]
WantedBy=multi-user.target
```

### Configurazione PANDA Dashboard

Crea il file `/etc/systemd/system/panda-dashboard.service`:

```ini
[Unit]
Description=PANDA Dashboard - Web Interface
After=network.target

[Service]
Type=simple
User=TUO_USERNAME
WorkingDirectory=/home/TUO_USERNAME/panda/dashboard
ExecStart=/usr/bin/python3 /home/TUO_USERNAME/panda/dashboard/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Attivazione Servizi

```bash
# Ricarica configurazione systemd
sudo systemctl daemon-reload

# Abilita avvio automatico
sudo systemctl enable panda
sudo systemctl enable panda-dashboard

# Avvia i servizi
sudo systemctl start panda
sudo systemctl start panda-dashboard

# Verifica stato
sudo systemctl status panda
sudo systemctl status panda-dashboard
```

### Comandi Utili

```bash
# Visualizza stato dettagliato
sudo systemctl status panda -l

# Vedi log in tempo reale
sudo journalctl -u panda -f

# Vedi ultimi 100 log
sudo journalctl -u panda -n 100

# Riavvia servizio
sudo systemctl restart panda

# Ferma servizio
sudo systemctl stop panda
```

### Permessi Sudo per Dashboard

Per permettere alla dashboard di controllare i servizi senza password, aggiungi a `/etc/sudoers`:

```
TUO_USERNAME ALL=(ALL) NOPASSWD: /bin/systemctl start panda
TUO_USERNAME ALL=(ALL) NOPASSWD: /bin/systemctl stop panda
TUO_USERNAME ALL=(ALL) NOPASSWD: /bin/systemctl restart panda
```

---

## Esempi Pratici di Utilizzo

### Esempio 1: Setup Progetto Python Completo

Questo esempio crea un progetto Python con struttura standard, tests e documentazione.

```json
{
  "tasks": [
    {
      "id": "step1_struttura",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea la struttura ~/progetti/myapi con cartelle: src/myapi, tests, docs"
    },
    {
      "id": "step2_init",
      "type": "file",
      "priority": 2,
      "filepath": "~/progetti/myapi/src/myapi/__init__.py",
      "prompt": "Crea __init__.py con versione 0.1.0 e docstring del package"
    },
    {
      "id": "step3_main",
      "type": "file",
      "priority": 3,
      "filepath": "~/progetti/myapi/src/myapi/main.py",
      "prompt": "Crea modulo main con classe ApiClient che ha metodi get() e post() con logging"
    },
    {
      "id": "step4_tests",
      "type": "file",
      "priority": 4,
      "filepath": "~/progetti/myapi/tests/test_main.py",
      "prompt": "Crea test pytest per ApiClient con mock delle richieste HTTP"
    },
    {
      "id": "step5_requirements",
      "type": "file",
      "priority": 5,
      "filepath": "~/progetti/myapi/requirements.txt",
      "prompt": "Crea requirements.txt con requests, pytest, pytest-mock"
    },
    {
      "id": "step6_readme",
      "type": "file",
      "priority": 6,
      "filepath": "~/progetti/myapi/README.md",
      "prompt": "Crea README professionale con: descrizione, installazione, uso, esempi, licenza MIT"
    }
  ]
}
```

### Esempio 2: Pipeline CI/CD Semplificata

```json
{
  "tasks": [
    {
      "id": "ci_lint",
      "type": "bash",
      "priority": 1,
      "prompt": "Esegui flake8 su ~/progetti/myapi/src con output dettagliato",
      "stop_on_fail": true
    },
    {
      "id": "ci_test",
      "type": "test",
      "priority": 2,
      "test_name": "Unit Tests",
      "test_command": "cd ~/progetti/myapi && python -m pytest tests/ -v",
      "expected": "passed",
      "stop_on_fail": true
    },
    {
      "id": "ci_build",
      "type": "bash",
      "priority": 3,
      "prompt": "Crea pacchetto distribuzione wheel di ~/progetti/myapi"
    },
    {
      "id": "ci_notify",
      "type": "python",
      "priority": 4,
      "prompt": "Stampa un messaggio di successo con data/ora e lista dei file in ~/progetti/myapi/dist"
    }
  ]
}
```

### Esempio 3: Manutenzione Sistema Automatizzata

```json
{
  "tasks": [
    {
      "id": "maint_disk_check",
      "type": "bash",
      "priority": 1,
      "prompt": "Mostra utilizzo disco in formato leggibile, ordina per uso decrescente"
    },
    {
      "id": "maint_cleanup_logs",
      "type": "bash",
      "priority": 2,
      "prompt": "Elimina file .log più vecchi di 30 giorni in ~/panda/logs"
    },
    {
      "id": "maint_cleanup_scripts",
      "type": "bash",
      "priority": 3,
      "prompt": "Elimina file temp_*.py più vecchi di 7 giorni in ~/panda/scripts"
    },
    {
      "id": "maint_backup",
      "type": "bash",
      "priority": 4,
      "prompt": "Crea backup compresso di ~/panda/config in ~/backups con data nel nome"
    },
    {
      "id": "maint_report",
      "type": "python",
      "priority": 5,
      "prompt": "Genera report HTML ~/panda/reports/maintenance.html con: spazio disco, numero file in panda, ultimi 5 task completati"
    }
  ]
}
```

### Esempio 4: Web Scraping e Report

```json
{
  "tasks": [
    {
      "id": "scrape_setup",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea cartella ~/scraping/output se non esiste"
    },
    {
      "id": "scrape_script",
      "type": "file",
      "priority": 2,
      "filepath": "~/scraping/scraper.py",
      "prompt": "Crea script Python che: 1) Usa requests per scaricare https://news.ycombinator.com, 2) Usa BeautifulSoup per estrarre titoli e link dei primi 10 articoli, 3) Salva risultato in JSON ~/scraping/output/hn_top10.json"
    },
    {
      "id": "scrape_run",
      "type": "bash",
      "priority": 3,
      "prompt": "Installa beautifulsoup4 con pip ed esegui ~/scraping/scraper.py"
    },
    {
      "id": "scrape_verify",
      "type": "test",
      "priority": 4,
      "test_name": "Verifica output scraping",
      "test_command": "cat ~/scraping/output/hn_top10.json | python -m json.tool",
      "expected": "title"
    }
  ]
}
```

---

## Sistema di Logging

### Struttura dei Log

PANDA produce log su due livelli:
1. **File giornalieri** in `~/panda/logs/YYYY-MM-DD.log`
2. **Output systemd** catturato da journalctl

### Formato Log

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] Messaggio
```

Esempio:
```
[2026-01-25 10:30:00] [INFO] 🐼 PANDA Worker v3.1 avviato
[2026-01-25 10:30:10] [INFO] ▶ Task backup_daily
[2026-01-25 10:30:45] [WARN] 🔁 Retry 1 for backup_daily
[2026-01-25 10:31:20] [INFO] ✅ Task backup_daily
[2026-01-25 10:31:20] [ERROR] Ollama error: Connection refused
```

### Livelli di Log

| Livello | Uso | Icona |
|---------|-----|-------|
| INFO | Operazioni normali | ▶ ✅ 🐼 |
| WARN | Situazioni anomale ma gestite | 🔁 🛑 |
| ERROR | Errori che richiedono attenzione | - |

### Rotazione Log

I log sono automaticamente separati per giorno. Per pulire log vecchi:

```bash
# Elimina log più vecchi di 30 giorni
find ~/panda/logs -name "*.log" -mtime +30 -delete

# Oppure crea un task PANDA per farlo
{
  "id": "cleanup_old_logs",
  "type": "bash",
  "priority": 99,
  "prompt": "Elimina file .log più vecchi di 30 giorni in ~/panda/logs"
}
```

### Analisi Log

Per analizzare i log:

```bash
# Conta errori di oggi
grep -c "\[ERROR\]" ~/panda/logs/$(date +%Y-%m-%d).log

# Trova tutti gli errori Ollama
grep "Ollama error" ~/panda/logs/*.log

# Task più frequenti
grep "▶ Task" ~/panda/logs/*.log | cut -d' ' -f5 | sort | uniq -c | sort -rn
```

---

## Gestione degli Errori e Retry

### Come Funziona il Retry

Quando un task fallisce, PANDA:
1. Incrementa il contatore `_retry` nel file task
2. Se `_retry < max_retries`: lascia il task in coda per nuovo tentativo
3. Se `_retry >= max_retries`: sposta in done/ con `success: false`

### Configurare i Retry

Nel file `panda.json`:
```json
{
  "max_retries": 3
}
```

Valori consigliati:
- **1-2**: Per task che probabilmente falliranno per motivi permanenti
- **3** (default): Buon bilanciamento
- **5+**: Per task con fallimenti intermittenti (rete, API esterne)

### Disabilitare Retry per Singolo Task

Aggiungi `"max_retries": 0` nel task stesso (non supportato attualmente, usa `stop_on_fail`).

### Stop on Fail

Per fermare l'intera pipeline al primo fallimento:

```json
{
  "id": "critical_task",
  "type": "bash",
  "prompt": "...",
  "stop_on_fail": true
}
```

Oppure globalmente per i test:
```json
{
  "stop_on_test_fail": true
}
```

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| Ollama error: Connection refused | Ollama non running | `ollama serve` o `systemctl start ollama` |
| Ollama error: timeout | Risposta troppo lenta | Aumenta timeout o usa modello più piccolo |
| exec_bash timeout | Comando troppo lento | Ottimizza il comando o aumenta timeout |
| File write error | Permessi o path invalido | Verifica permessi e che il path esista |

---

## Prompt Engineering: Best Practices

### Principi Fondamentali

1. **Sii Specifico**: Più dettagli dai, migliore il risultato
2. **Un Task = Un'Azione**: Non sovraccaricare un singolo prompt
3. **Specifica il Formato**: Dì esattamente come vuoi l'output
4. **Dai Contesto**: Menziona tecnologie, versioni, vincoli

### Template Efficaci

#### Per Comandi Bash
```
Genera SOLO il comando bash per: [descrizione]
Sistema operativo: Linux Mint
Non usare sudo a meno che non sia necessario.
```

#### Per Codice Python
```
Scrivi codice Python 3 che:
1. [primo requisito]
2. [secondo requisito]
3. [terzo requisito]

Vincoli:
- Usa solo librerie standard (no pip install)
- Massimo 50 righe
- Includi gestione errori base
```

#### Per File di Configurazione
```
Crea un file [tipo] per [scopo].
Deve includere:
- [elemento 1]
- [elemento 2]
Formato: [JSON/YAML/INI]
Commenta le opzioni non ovvie.
```

### Esempi Confronto

❌ **Prompt Vago:**
```
fai un sito
```

✅ **Prompt Efficace:**
```
Crea una pagina HTML5 single-page per un portfolio personale.
Includi:
- Header con nome "Mario Rossi" e tagline "Web Developer"
- Sezione "About" con 2 paragrafi placeholder
- Sezione "Skills" con lista di 5 skill
- Footer con copyright 2026
Stile: CSS inline, tema scuro (#1a1a2e sfondo, #e0e0e0 testo), font system-ui
```

### Prompt per Diversi Linguaggi

**JavaScript:**
```
Scrivi una funzione JavaScript ES6+ che [descrizione].
- Usa arrow functions
- Async/await per operazioni asincrone
- Nessuna dipendenza esterna
```

**SQL:**
```
Scrivi una query SQL per [descrizione].
Database: PostgreSQL 15
Tabelle coinvolte: [lista]
Ottimizza per performance su tabelle con 1M+ righe.
```

**Bash Script:**
```
Crea uno script bash che [descrizione].
- Deve essere compatibile con bash 4+
- Usa set -e per exit on error
- Logga le operazioni con timestamp
- Accetta parametri: $1 = [param1], $2 = [param2]
```

---

## Troubleshooting e Risoluzione Problemi

### PANDA Worker Non Parte

**Sintomi:** Il servizio rimane in stato "failed" o non risponde

**Diagnosi:**
```bash
# Controlla stato servizio
sudo systemctl status panda

# Vedi log recenti
sudo journalctl -u panda -n 50

# Prova avvio manuale
python3 ~/panda/worker.py
```

**Cause comuni:**
1. Python non trovato: verifica `which python3`
2. Dipendenze mancanti: `pip install flask requests`
3. Errore sintassi in panda.json: verifica con `python -m json.tool ~/panda/config/panda.json`
4. Ollama non raggiungibile: verifica `curl http://localhost:11434/api/tags`

### Dashboard Non Risponde

**Sintomi:** Browser mostra "Connection refused" o timeout

**Diagnosi:**
```bash
# Controlla porta
ss -tlnp | grep 5000

# Controlla servizio
sudo systemctl status panda-dashboard

# Avvia manualmente
python3 ~/panda/dashboard/server.py
```

**Cause comuni:**
1. Porta 5000 già in uso: trova il processo con `lsof -i :5000`
2. Firewall blocca: `sudo ufw allow 5000`
3. Flask non installato: `pip install flask`

### Task Falliscono Sempre

**Sintomi:** Tutti i task finiscono con success=false

**Diagnosi:**
```bash
# Vedi ultimo risultato
ls -t ~/panda/results/*.json | head -1 | xargs cat

# Controlla log per errori
grep ERROR ~/panda/logs/$(date +%Y-%m-%d).log
```

**Cause comuni:**
1. Ollama non risponde: riavvia con `systemctl restart ollama`
2. Modello non scaricato: `ollama pull qwen2.5-coder:7b`
3. Modello sbagliato in config: verifica che corrisponda a `ollama list`

### Ollama Molto Lento

**Sintomi:** Task impiegano minuti per completare

**Diagnosi:**
```bash
# Controlla uso risorse
htop

# Testa velocità Ollama
time ollama run qwen2.5-coder:7b "print hello"
```

**Soluzioni:**
1. Usa modello più piccolo: cambia in config `"model": "qwen2.5-coder:3b"`
2. Chiudi applicazioni pesanti
3. Verifica che non ci siano altri processi LLM in esecuzione

### Output LLM Contiene "Spazzatura"

**Sintomi:** Il codice generato contiene prefazioni o markdown

**Causa:** La funzione `clean_llm` non ha catturato il pattern

**Soluzione temporanea:** Modifica il prompt per essere più esplicito:
```
IMPORTANTE: Rispondi SOLO con il codice.
NIENTE testo prima o dopo.
NIENTE markdown ``` blocchi.
Inizia direttamente con la prima riga di codice.
```

### Disco Pieno

**Sintomi:** Task falliscono con errori di scrittura

**Diagnosi:**
```bash
df -h ~/panda
```

**Soluzioni:**
```bash
# Pulisci risultati vecchi
find ~/panda/results -name "*.json" -mtime +30 -delete

# Pulisci script temporanei
find ~/panda/scripts -name "temp_*.py" -mtime +7 -delete

# Pulisci log vecchi
find ~/panda/logs -name "*.log" -mtime +30 -delete
```

---

## Sicurezza e Considerazioni

### Rischi Potenziali

PANDA esegue codice generato da AI con i permessi dell'utente. Questo comporta rischi:

1. **Comandi Distruttivi**: L'LLM potrebbe generare `rm -rf /` se mal-promptato
2. **Esfiltrazione Dati**: Codice potrebbe inviare dati a server esterni
3. **Privilege Escalation**: Se l'utente ha sudo, anche PANDA lo ha

### Mitigazioni

#### 1. Utente Dedicato
Crea un utente dedicato per PANDA con permessi limitati:
```bash
sudo useradd -m -s /bin/bash panda
sudo -u panda mkdir -p /home/panda/panda
```

#### 2. Disabilita Esecuzione
In ambienti sensibili, genera senza eseguire:
```json
{
  "execute_bash": false,
  "execute_code": false,
  "modify_files": true
}
```

#### 3. Network Isolation
Se possibile, esegui PANDA in una VM o container senza accesso a rete esterna.

#### 4. Revisione Manuale
Per task critici, genera prima il codice (type=prompt) e revisiona prima di eseguire.

### Accesso alla Dashboard

La dashboard non ha autenticazione. Per ambienti non-localhost:

1. **VPN**: Accedi solo via VPN
2. **Reverse Proxy con Auth**: Usa nginx con autenticazione basic
3. **Firewall**: Limita accesso a IP specifici

```bash
# Esempio: accesso solo da IP specifico
sudo ufw allow from 192.168.1.100 to any port 5000
```

### Log Sensibili

I log possono contenere output di comandi con dati sensibili. Considera:
- Rotazione automatica
- Permessi restrittivi: `chmod 600 ~/panda/logs/*.log`
- Esclusione da backup cloud

---

## Appendice: Riferimenti Rapidi

### Comandi Systemd Essenziali

```bash
# Worker
sudo systemctl start panda
sudo systemctl stop panda
sudo systemctl restart panda
sudo systemctl status panda
journalctl -u panda -f

# Dashboard
sudo systemctl start panda-dashboard
sudo systemctl stop panda-dashboard
sudo systemctl status panda-dashboard
```

### Curl API Rapidi

```bash
# Stato
curl http://localhost:5000/api/status

# Lista pending
curl http://localhost:5000/api/tasks/pending

# Aggiungi task
curl -X POST http://localhost:5000/api/tasks/add \
  -H "Content-Type: application/json" \
  -d '{"id":"test","type":"bash","prompt":"echo hello"}'

# Import multipli
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"id":"t1","type":"bash","prompt":"ls"}]}'
```

### Path Importanti

| Path | Descrizione |
|------|-------------|
| `~/panda/worker.py` | Script principale worker |
| `~/panda/config/panda.json` | Configurazione |
| `~/panda/tasks/` | Coda task |
| `~/panda/tasks/done/` | Task completati |
| `~/panda/results/` | Risultati esecuzione |
| `~/panda/logs/` | Log giornalieri |
| `~/panda/status/current.json` | Stato real-time |
| `~/panda/dashboard/server.py` | Server Flask |

### Struttura JSON Task

```json
{
  "id": "nome_task",
  "type": "prompt|bash|python|file|test|multi",
  "priority": 10,
  "prompt": "Istruzioni",
  "filepath": "solo per type=file",
  "test_command": "solo per type=test",
  "expected": "solo per type=test",
  "steps": ["solo per type=multi"],
  "stop_on_fail": false
}
```

### Troubleshooting Rapido

| Problema | Comando Diagnosi |
|----------|------------------|
| PANDA non parte | `sudo journalctl -u panda -n 50` |
| Task falliscono | `cat ~/panda/results/*.json \| tail -1` |
| Ollama lento | `htop` + modello più piccolo |
| Dashboard down | `python3 ~/panda/dashboard/server.py` |
| Disco pieno | `df -h ~/panda && find ~/panda -size +10M` |

---

## Documenti Correlati

- **[GUIDA_IMPORT_MASSIVO.md](GUIDA_IMPORT_MASSIVO.md)** - Guida completa all'importazione massiva di task

---

*Documentazione PANDA v3.1 - Generata Gennaio 2026*
*Per supporto e contributi, consulta il repository del progetto.*
