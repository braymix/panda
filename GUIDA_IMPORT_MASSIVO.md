# Guida Completa all'Import Massivo di Task in PANDA

## Tutto Quello Che Devi Sapere per Importare Task in Massa

**Versione:** 1.0
**Data:** Gennaio 2026
**Compatibile con:** PANDA v3.1

---

## Indice

1. [Introduzione all'Import Massivo](#introduzione-allimport-massivo)
2. [Perché Usare l'Import Massivo](#perché-usare-limport-massivo)
3. [Prerequisiti e Preparazione](#prerequisiti-e-preparazione)
4. [Formato JSON per l'Import](#formato-json-per-limport)
5. [Metodi di Import Disponibili](#metodi-di-import-disponibili)
6. [Import via Dashboard Web](#import-via-dashboard-web)
7. [Import via cURL](#import-via-curl)
8. [Import via Python](#import-via-python)
9. [Import via File JSON](#import-via-file-json)
10. [Gestione delle Priorità](#gestione-delle-priorità)
11. [Esempi Pratici Completi](#esempi-pratici-completi)
12. [Validazione del JSON](#validazione-del-json)
13. [Gestione degli Errori](#gestione-degli-errori)
14. [Best Practices](#best-practices)
15. [Casi d'Uso Avanzati](#casi-duso-avanzati)
16. [Script di Utilità](#script-di-utilità)
17. [Troubleshooting Import](#troubleshooting-import)
18. [FAQ - Domande Frequenti](#faq---domande-frequenti)

---

## Introduzione all'Import Massivo

### Cos'è l'Import Massivo?

L'import massivo è una funzionalità di PANDA che permette di inserire molteplici task nella coda di esecuzione con una singola operazione. Invece di creare i task uno alla volta attraverso il form della dashboard o chiamate API singole, puoi preparare un documento JSON contenente decine, centinaia o migliaia di task e importarli tutti insieme.

Questa funzionalità è esposta attraverso l'endpoint API `POST /api/tasks/import` e può essere utilizzata sia dalla dashboard web sia programmaticamente tramite script o chiamate HTTP dirette.

### Come Funziona Internamente

Quando invii una richiesta di import massivo, ecco cosa succede dietro le quinte:

1. **Ricezione**: Il server Flask riceve il payload JSON sulla rotta `/api/tasks/import`
2. **Parsing**: Il JSON viene parsato e viene estratto l'array `tasks`
3. **Iterazione**: Per ogni task nell'array:
   - Viene generato un ID se non presente (`task_{timestamp}`)
   - Viene creato un filename univoco: `task_{timestamp}_{id}.json`
   - Il task viene scritto come file JSON nella directory `~/panda/tasks/`
   - Si attende 10ms prima del prossimo task (per evitare collisioni di timestamp)
4. **Risposta**: Viene restituito un riepilogo con numero di task importati e lista dei filename

### Limitazioni Tecniche

È importante essere consapevoli delle limitazioni attuali:

- **Nessun supporto nativo CSV/Excel**: I dati devono essere in formato JSON
- **Nessuna validazione schema**: Task malformati verranno importati ma falliranno all'esecuzione
- **Nessun limite di dimensione**: Teoricamente puoi importare migliaia di task, ma considera le performance
- **Nessuna transazione**: Se l'import fallisce a metà, i task già creati rimarranno
- **Delay tra task**: 10ms di pausa tra ogni task per evitare collisioni di timestamp

---

## Perché Usare l'Import Massivo

### Scenari Ideali

L'import massivo è la scelta giusta quando:

#### 1. Setup Iniziale di Progetti
Quando devi configurare un nuovo progetto con decine di file da generare, l'import massivo ti permette di definire tutto in anticipo e lasciare che PANDA lavori autonomamente.

#### 2. Pipeline di Build/Deploy
Per workflow CI/CD con molti step (lint, test, build, deploy), puoi preparare l'intera pipeline in un JSON e importarla con un comando.

#### 3. Generazione Contenuti in Massa
Devi generare 50 pagine HTML per un sito? 100 unit test? Definisci i task una volta e importa.

#### 4. Automazione Ripetitiva
Task che esegui regolarmente (backup settimanali, report mensili) possono essere predefiniti in JSON e reimportati quando necessario.

#### 5. Migrazione e Setup Ambienti
Quando configuri un nuovo server o ambiente di sviluppo, l'import massivo permette di replicare setup complessi.

### Vantaggi rispetto all'Import Singolo

| Aspetto | Import Singolo | Import Massivo |
|---------|----------------|----------------|
| Velocità | 1 task alla volta | N task in una chiamata |
| Automazione | Richiede interazione | Completamente scriptabile |
| Ripetibilità | Manuale | JSON riutilizzabile |
| Versionamento | Difficile | JSON committabile in git |
| Collaborazione | Individuale | JSON condivisibile |

---

## Prerequisiti e Preparazione

### Verifica Sistema PANDA

Prima di procedere con l'import, assicurati che PANDA sia operativo:

```bash
# Verifica che il worker sia attivo
sudo systemctl status panda
# Output atteso: "active (running)"

# Verifica che la dashboard sia attiva
sudo systemctl status panda-dashboard
# Output atteso: "active (running)"

# Verifica che l'API risponda
curl http://localhost:5000/api/status
# Output atteso: {"panda_running": true, ...}

# Verifica che Ollama sia disponibile (necessario per esecuzione)
curl http://localhost:11434/api/tags
# Output atteso: JSON con modelli disponibili
```

### Verifica Spazio Disco

L'import crea file JSON nella directory tasks. Verifica lo spazio disponibile:

```bash
df -h ~/panda
# Assicurati di avere almeno qualche GB libero per import grandi
```

### Strumenti Necessari

Per lavorare con l'import massivo, ti serviranno:

- **curl**: Per chiamate API da terminale (`apt install curl`)
- **jq**: Per manipolazione JSON (`apt install jq`)
- **python3**: Per script di import avanzati
- **Un editor di testo**: Per creare i file JSON (VSCode, nano, vim)

---

## Formato JSON per l'Import

### Struttura Base

Il formato JSON per l'import massivo ha una struttura semplice ma rigorosa:

```json
{
  "tasks": [
    {
      "id": "task_1",
      "type": "bash",
      "priority": 1,
      "prompt": "Descrizione del task"
    },
    {
      "id": "task_2",
      "type": "python",
      "priority": 2,
      "prompt": "Descrizione del task"
    }
  ]
}
```

L'oggetto root deve avere una chiave `tasks` contenente un array di oggetti task.

### Campi di Ogni Task

Ogni task nell'array può avere i seguenti campi:

#### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `type` | string | Tipo di task: `prompt`, `bash`, `python`, `file`, `test`, `multi` |
| `prompt` | string | Istruzioni per l'LLM (non richiesto per `test`) |

#### Campi Opzionali ma Consigliati

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `id` | string | auto-generato | Identificativo univoco del task |
| `priority` | integer | 10 | Priorità esecuzione (1 = massima) |

#### Campi Specifici per Tipo

| Campo | Tipi | Descrizione |
|-------|------|-------------|
| `filepath` | file | Percorso dove salvare il file generato |
| `test_name` | test | Nome descrittivo del test |
| `test_command` | test | Comando da eseguire |
| `expected` | test | Stringa attesa nell'output |
| `steps` | multi | Array di step da eseguire |
| `stop_on_fail` | tutti | Se true, ferma pipeline su fallimento |
| `prompt_file` | tutti | Path a file con prompt lungo |

### Esempio Completo con Tutti i Tipi

```json
{
  "tasks": [
    {
      "id": "esempio_prompt",
      "type": "prompt",
      "priority": 1,
      "prompt": "Spiega il concetto di container Docker in 3 frasi"
    },
    {
      "id": "esempio_bash",
      "type": "bash",
      "priority": 2,
      "prompt": "Elenca tutti i file .py nella home directory"
    },
    {
      "id": "esempio_python",
      "type": "python",
      "priority": 3,
      "prompt": "Calcola e stampa i primi 10 numeri della serie di Fibonacci"
    },
    {
      "id": "esempio_file",
      "type": "file",
      "priority": 4,
      "filepath": "~/panda/output/hello.py",
      "prompt": "Crea uno script Python che stampa Hello World"
    },
    {
      "id": "esempio_test",
      "type": "test",
      "priority": 5,
      "test_name": "Verifica Python installato",
      "test_command": "python3 --version",
      "expected": "Python 3"
    },
    {
      "id": "esempio_multi",
      "type": "multi",
      "priority": 6,
      "steps": [
        {"type": "bash", "prompt": "Crea directory ~/test_multi"},
        {"type": "file", "filepath": "~/test_multi/app.py", "prompt": "Crea script hello world"},
        {"type": "bash", "prompt": "Esegui python3 ~/test_multi/app.py"}
      ]
    }
  ]
}
```

---

## Metodi di Import Disponibili

PANDA offre quattro metodi principali per l'import massivo. Ognuno ha i suoi vantaggi a seconda del contesto d'uso.

### Panoramica Metodi

| Metodo | Interattività | Automazione | Complessità |
|--------|---------------|-------------|-------------|
| Dashboard Web | Alta | Bassa | Minima |
| cURL | Media | Alta | Bassa |
| Python Script | Bassa | Massima | Media |
| File JSON + cURL | Bassa | Alta | Bassa |

### Quale Metodo Scegliere?

- **Dashboard Web**: Per import occasionali e piccoli (< 20 task)
- **cURL**: Per automazione da script bash o cron
- **Python**: Per logiche complesse, generazione dinamica, o integrazione con altri sistemi
- **File JSON**: Per task predefiniti da eseguire ripetutamente

---

## Import via Dashboard Web

### Accesso alla Sezione Import

1. Apri il browser e vai a `http://localhost:5000` (o l'IP del tuo server PANDA)
2. Scorri fino alla sezione "📥 Importa Task da JSON"
3. Vedrai una textarea e un pulsante "Importa Tasks"

### Procedura Passo-Passo

#### Passo 1: Prepara il JSON

Crea il tuo JSON in un editor di testo. Esempio minimo:

```json
{
  "tasks": [
    {"id": "test1", "type": "bash", "priority": 1, "prompt": "echo Ciao"},
    {"id": "test2", "type": "bash", "priority": 2, "prompt": "echo Mondo"}
  ]
}
```

#### Passo 2: Incolla nella Textarea

Copia tutto il JSON e incollalo nella textarea della dashboard.

#### Passo 3: Clicca "Importa Tasks"

Dopo il click, vedrai:
- Un alert con il numero di task importati: "Importati 2 task!"
- La textarea verrà svuotata
- La sezione "Coda Task" si aggiornerà mostrando i nuovi task

#### Passo 4: Verifica

Controlla la sezione "Coda Task" per vedere i task appena importati ordinati per priorità.

### Screenshot Concettuale

```
┌─────────────────────────────────────────────────┐
│ 📥 Importa Task da JSON                          │
├─────────────────────────────────────────────────┤
│ 📖 Formato                                       │
│ {"tasks":[                                       │
│   {"id":"nome","type":"bash","priority":1,...}  │
│ ]}                                               │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ {"tasks":[                                  │ │
│ │   {"id":"test1","type":"bash",...},         │ │
│ │   {"id":"test2","type":"bash",...}          │ │
│ │ ]}                                          │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [     📥 Importa Tasks                        ]  │
└─────────────────────────────────────────────────┘
```

### Gestione Errori nella Dashboard

Se il JSON non è valido, vedrai un alert di errore:
```
"JSON non valido: Unexpected token..."
```

Verifica:
- Che le virgolette siano doppie `"`, non singole `'`
- Che non ci siano virgole finali dopo l'ultimo elemento
- Che le parentesi siano bilanciate

---

## Import via cURL

### Comando Base

Il comando cURL per l'import è:

```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[...]}'
```

### Esempio Minimale

```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"id":"hello","type":"bash","priority":1,"prompt":"echo Hello World"}]}'
```

**Output:**
```json
{"success":true,"imported":1,"filenames":["task_1706177700_hello.json"]}
```

### Esempio con Multipli Task

```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"id": "step1", "type": "bash", "priority": 1, "prompt": "mkdir -p ~/test"},
      {"id": "step2", "type": "file", "priority": 2, "filepath": "~/test/hello.txt", "prompt": "Scrivi Hello World"},
      {"id": "step3", "type": "bash", "priority": 3, "prompt": "cat ~/test/hello.txt"}
    ]
  }'
```

### Import da Server Remoto

Se PANDA gira su un altro server:

```bash
curl -X POST http://192.168.1.100:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"id":"remote_test","type":"bash","priority":1,"prompt":"hostname"}]}'
```

### Salvare la Risposta

Per salvare la risposta in un file:

```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[...]}' \
  -o import_result.json
```

### Verbose Mode per Debug

Per vedere dettagli della comunicazione HTTP:

```bash
curl -v -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"id":"debug","type":"bash","prompt":"ls"}]}'
```

### Uso con jq per Parsing

Combina cURL con jq per estrarre informazioni:

```bash
# Conta task importati
curl -s -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[...]}' | jq '.imported'

# Lista filename creati
curl -s -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d '{"tasks":[...]}' | jq '.filenames[]'
```

---

## Import via Python

### Script Base

```python
import requests
import json

def import_tasks(tasks, base_url="http://localhost:5000"):
    """
    Importa una lista di task in PANDA.

    Args:
        tasks: Lista di dizionari task
        base_url: URL base della dashboard PANDA

    Returns:
        dict: Risposta dell'API
    """
    url = f"{base_url}/api/tasks/import"
    payload = {"tasks": tasks}

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    response.raise_for_status()
    return response.json()

# Esempio d'uso
tasks = [
    {"id": "python_task_1", "type": "bash", "priority": 1, "prompt": "date"},
    {"id": "python_task_2", "type": "bash", "priority": 2, "prompt": "uptime"}
]

result = import_tasks(tasks)
print(f"Importati {result['imported']} task")
print(f"Filenames: {result['filenames']}")
```

### Script Avanzato con Gestione Errori

```python
import requests
import json
import sys
from typing import List, Dict, Optional

class PandaImporter:
    """Classe per gestire import massivo in PANDA."""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.import_url = f"{base_url}/api/tasks/import"

    def check_connection(self) -> bool:
        """Verifica che PANDA sia raggiungibile."""
        try:
            r = requests.get(f"{self.base_url}/api/status", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def validate_task(self, task: Dict) -> List[str]:
        """Valida un singolo task e ritorna lista errori."""
        errors = []

        # Campi obbligatori
        if "type" not in task:
            errors.append("Campo 'type' mancante")
        elif task["type"] not in ["prompt", "bash", "python", "file", "test", "multi"]:
            errors.append(f"Tipo '{task['type']}' non valido")

        # Validazione per tipo
        task_type = task.get("type", "")

        if task_type in ["prompt", "bash", "python", "file"]:
            if "prompt" not in task:
                errors.append(f"Campo 'prompt' richiesto per tipo '{task_type}'")

        if task_type == "file":
            if "filepath" not in task:
                errors.append("Campo 'filepath' richiesto per tipo 'file'")

        if task_type == "test":
            if "test_command" not in task:
                errors.append("Campo 'test_command' richiesto per tipo 'test'")

        if task_type == "multi":
            if "steps" not in task or not isinstance(task["steps"], list):
                errors.append("Campo 'steps' (array) richiesto per tipo 'multi'")

        # Validazione priorità
        if "priority" in task:
            if not isinstance(task["priority"], int) or task["priority"] < 1:
                errors.append("Priority deve essere intero >= 1")

        return errors

    def validate_all(self, tasks: List[Dict]) -> Dict[str, List]:
        """Valida tutti i task e ritorna report errori."""
        all_errors = {}
        for i, task in enumerate(tasks):
            task_id = task.get("id", f"task_{i}")
            errors = self.validate_task(task)
            if errors:
                all_errors[task_id] = errors
        return all_errors

    def import_tasks(self, tasks: List[Dict], validate: bool = True) -> Dict:
        """
        Importa task in PANDA.

        Args:
            tasks: Lista di task da importare
            validate: Se True, valida prima di importare

        Returns:
            Risposta API con campi aggiuntivi
        """
        # Check connessione
        if not self.check_connection():
            return {
                "success": False,
                "error": "PANDA non raggiungibile",
                "imported": 0
            }

        # Validazione opzionale
        if validate:
            errors = self.validate_all(tasks)
            if errors:
                return {
                    "success": False,
                    "error": "Validazione fallita",
                    "validation_errors": errors,
                    "imported": 0
                }

        # Import
        try:
            response = requests.post(
                self.import_url,
                json={"tasks": tasks},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0
            }

    def import_from_file(self, filepath: str) -> Dict:
        """Importa task da file JSON."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            tasks = data.get("tasks", [])
            return self.import_tasks(tasks)
        except FileNotFoundError:
            return {"success": False, "error": f"File {filepath} non trovato"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON non valido: {e}"}


# Esempio d'uso
if __name__ == "__main__":
    importer = PandaImporter()

    # Check connessione
    if not importer.check_connection():
        print("ERRORE: PANDA non raggiungibile")
        sys.exit(1)

    # Definisci task
    tasks = [
        {
            "id": "setup_dir",
            "type": "bash",
            "priority": 1,
            "prompt": "Crea directory ~/python_import_test"
        },
        {
            "id": "create_script",
            "type": "file",
            "priority": 2,
            "filepath": "~/python_import_test/main.py",
            "prompt": "Crea script Python che stampa data e ora corrente"
        },
        {
            "id": "run_script",
            "type": "bash",
            "priority": 3,
            "prompt": "Esegui python3 ~/python_import_test/main.py"
        }
    ]

    # Valida prima
    errors = importer.validate_all(tasks)
    if errors:
        print("Errori di validazione:")
        for task_id, task_errors in errors.items():
            print(f"  {task_id}: {', '.join(task_errors)}")
        sys.exit(1)

    # Importa
    result = importer.import_tasks(tasks)

    if result["success"]:
        print(f"Importati {result['imported']} task!")
        for filename in result["filenames"]:
            print(f"  - {filename}")
    else:
        print(f"Errore: {result.get('error', 'Sconosciuto')}")
```

### Generazione Dinamica di Task

```python
def generate_file_tasks(files_config):
    """
    Genera task di tipo file da una configurazione.

    Args:
        files_config: Lista di tuple (filepath, descrizione)

    Returns:
        Lista di task pronti per import
    """
    tasks = []
    for i, (filepath, description) in enumerate(files_config, start=1):
        tasks.append({
            "id": f"gen_file_{i}",
            "type": "file",
            "priority": i,
            "filepath": filepath,
            "prompt": description
        })
    return tasks

# Esempio: genera 10 componenti React
components = [
    ("~/project/src/components/Header.jsx", "Crea componente React Header con navigazione"),
    ("~/project/src/components/Footer.jsx", "Crea componente React Footer con copyright"),
    ("~/project/src/components/Sidebar.jsx", "Crea componente React Sidebar con menu"),
    ("~/project/src/components/Card.jsx", "Crea componente React Card riutilizzabile"),
    ("~/project/src/components/Button.jsx", "Crea componente React Button con varianti"),
]

tasks = generate_file_tasks(components)
result = importer.import_tasks(tasks)
```

---

## Import via File JSON

### Creazione del File

Crea un file `tasks_to_import.json`:

```json
{
  "tasks": [
    {
      "id": "from_file_1",
      "type": "bash",
      "priority": 1,
      "prompt": "Mostra la data corrente"
    },
    {
      "id": "from_file_2",
      "type": "python",
      "priority": 2,
      "prompt": "Stampa Hello from file import"
    }
  ]
}
```

### Import con cURL

```bash
curl -X POST http://localhost:5000/api/tasks/import \
  -H "Content-Type: application/json" \
  -d @tasks_to_import.json
```

Il simbolo `@` indica a cURL di leggere il body dal file.

### Script Bash per Import da File

```bash
#!/bin/bash
# import_from_file.sh

PANDA_URL="${PANDA_URL:-http://localhost:5000}"
FILE="$1"

if [ -z "$FILE" ]; then
    echo "Uso: $0 <file.json>"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "Errore: File $FILE non trovato"
    exit 1
fi

# Valida JSON
if ! python3 -m json.tool "$FILE" > /dev/null 2>&1; then
    echo "Errore: JSON non valido in $FILE"
    exit 1
fi

# Import
RESULT=$(curl -s -X POST "$PANDA_URL/api/tasks/import" \
    -H "Content-Type: application/json" \
    -d @"$FILE")

# Parse risultato
SUCCESS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))")
IMPORTED=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('imported', 0))")

if [ "$SUCCESS" = "True" ]; then
    echo "Successo! Importati $IMPORTED task."
else
    echo "Errore nell'import"
    echo "$RESULT"
    exit 1
fi
```

Uso:
```bash
chmod +x import_from_file.sh
./import_from_file.sh tasks_to_import.json
```

### Organizzazione File per Progetti

Struttura consigliata per progetti con molti task predefiniti:

```
~/panda_tasks/
├── setup/
│   ├── project_init.json      # Task setup iniziale
│   └── dependencies.json      # Task installazione dipendenze
├── build/
│   ├── compile.json           # Task compilazione
│   └── package.json           # Task packaging
├── deploy/
│   ├── staging.json           # Deploy su staging
│   └── production.json        # Deploy su produzione
└── maintenance/
    ├── backup.json            # Task backup
    └── cleanup.json           # Task pulizia
```

Import selettivo:
```bash
# Solo setup
curl -X POST http://localhost:5000/api/tasks/import -H "Content-Type: application/json" -d @~/panda_tasks/setup/project_init.json

# Pipeline completa
for f in ~/panda_tasks/build/*.json; do
    curl -X POST http://localhost:5000/api/tasks/import -H "Content-Type: application/json" -d @"$f"
done
```

---

## Gestione delle Priorità

### Come Funzionano le Priorità

In PANDA, la priorità determina l'ordine di esecuzione dei task:

- **Priorità 1**: Eseguito per primo
- **Priorità 10**: Default, eseguito dopo priorità inferiori
- **Priorità 99**: Eseguito per ultimo

I task con stessa priorità vengono eseguiti nell'ordine di creazione (timestamp del filename).

### Strategie di Priorità per Import Massivo

#### Strategia Sequenziale

Quando i task devono essere eseguiti in un ordine specifico:

```json
{
  "tasks": [
    {"id": "step1", "priority": 1, "type": "bash", "prompt": "Primo"},
    {"id": "step2", "priority": 2, "type": "bash", "prompt": "Secondo"},
    {"id": "step3", "priority": 3, "type": "bash", "prompt": "Terzo"}
  ]
}
```

#### Strategia a Livelli

Raggruppare task per fase:

```json
{
  "tasks": [
    {"id": "setup_1", "priority": 10, "type": "bash", "prompt": "Setup A"},
    {"id": "setup_2", "priority": 10, "type": "bash", "prompt": "Setup B"},
    {"id": "build_1", "priority": 20, "type": "bash", "prompt": "Build A"},
    {"id": "build_2", "priority": 20, "type": "bash", "prompt": "Build B"},
    {"id": "test_1", "priority": 30, "type": "test", "test_command": "...", "expected": "..."}
  ]
}
```

#### Strategia Critico-Prima

Task critici con priorità bassa, task opzionali con priorità alta:

```json
{
  "tasks": [
    {"id": "critical_backup", "priority": 1, "type": "bash", "prompt": "Backup DB"},
    {"id": "critical_migrate", "priority": 2, "type": "bash", "prompt": "Migrate DB"},
    {"id": "optional_cleanup", "priority": 99, "type": "bash", "prompt": "Cleanup temp"}
  ]
}
```

### Generazione Automatica Priorità

Script Python per assegnare priorità incrementali:

```python
def assign_sequential_priority(tasks, start=1):
    """Assegna priorità sequenziali ai task."""
    for i, task in enumerate(tasks, start=start):
        task["priority"] = i
    return tasks

def assign_grouped_priority(tasks, group_size=5, start=10, increment=10):
    """Assegna stessa priorità a gruppi di task."""
    current_priority = start
    for i, task in enumerate(tasks):
        if i > 0 and i % group_size == 0:
            current_priority += increment
        task["priority"] = current_priority
    return tasks
```

---

## Esempi Pratici Completi

### Esempio 1: Setup Ambiente di Sviluppo Python

```json
{
  "tasks": [
    {
      "id": "dev_create_venv",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea virtual environment Python in ~/dev/myproject/.venv"
    },
    {
      "id": "dev_gitignore",
      "type": "file",
      "priority": 2,
      "filepath": "~/dev/myproject/.gitignore",
      "prompt": "Crea .gitignore completo per progetto Python con venv, __pycache__, .env, IDE files"
    },
    {
      "id": "dev_requirements",
      "type": "file",
      "priority": 3,
      "filepath": "~/dev/myproject/requirements.txt",
      "prompt": "Crea requirements.txt con: flask, requests, python-dotenv, pytest, black, flake8"
    },
    {
      "id": "dev_requirements_dev",
      "type": "file",
      "priority": 4,
      "filepath": "~/dev/myproject/requirements-dev.txt",
      "prompt": "Crea requirements-dev.txt con: pytest-cov, mypy, ipython, pre-commit"
    },
    {
      "id": "dev_install_deps",
      "type": "bash",
      "priority": 5,
      "prompt": "Attiva venv ~/dev/myproject/.venv e installa requirements.txt e requirements-dev.txt"
    },
    {
      "id": "dev_precommit",
      "type": "file",
      "priority": 6,
      "filepath": "~/dev/myproject/.pre-commit-config.yaml",
      "prompt": "Crea configurazione pre-commit con black, flake8, mypy hooks"
    },
    {
      "id": "dev_pyproject",
      "type": "file",
      "priority": 7,
      "filepath": "~/dev/myproject/pyproject.toml",
      "prompt": "Crea pyproject.toml con configurazione black, mypy, pytest per progetto 'myproject'"
    },
    {
      "id": "dev_src_init",
      "type": "file",
      "priority": 8,
      "filepath": "~/dev/myproject/src/myproject/__init__.py",
      "prompt": "Crea __init__.py con __version__ = '0.1.0' e docstring package"
    },
    {
      "id": "dev_main",
      "type": "file",
      "priority": 9,
      "filepath": "~/dev/myproject/src/myproject/main.py",
      "prompt": "Crea main.py con funzione main() che logga 'Application started' e entry point if __name__"
    },
    {
      "id": "dev_test_init",
      "type": "bash",
      "priority": 10,
      "prompt": "Crea directory ~/dev/myproject/tests con file __init__.py vuoto"
    },
    {
      "id": "dev_test_main",
      "type": "file",
      "priority": 11,
      "filepath": "~/dev/myproject/tests/test_main.py",
      "prompt": "Crea test pytest che importa e testa la funzione main del modulo myproject.main"
    },
    {
      "id": "dev_readme",
      "type": "file",
      "priority": 12,
      "filepath": "~/dev/myproject/README.md",
      "prompt": "Crea README.md professionale con: titolo, descrizione, requisiti, installazione, uso, test, licenza MIT"
    },
    {
      "id": "dev_git_init",
      "type": "bash",
      "priority": 13,
      "prompt": "Inizializza repository git in ~/dev/myproject"
    },
    {
      "id": "dev_verify",
      "type": "test",
      "priority": 14,
      "test_name": "Verifica setup completato",
      "test_command": "cd ~/dev/myproject && source .venv/bin/activate && python -c 'from myproject.main import main; print(\"OK\")'",
      "expected": "OK"
    }
  ]
}
```

### Esempio 2: Pipeline Build e Test React

```json
{
  "tasks": [
    {
      "id": "react_lint",
      "type": "bash",
      "priority": 1,
      "prompt": "Esegui npm run lint in ~/webapp e mostra errori",
      "stop_on_fail": true
    },
    {
      "id": "react_typecheck",
      "type": "bash",
      "priority": 2,
      "prompt": "Esegui npm run typecheck (tsc --noEmit) in ~/webapp",
      "stop_on_fail": true
    },
    {
      "id": "react_test",
      "type": "test",
      "priority": 3,
      "test_name": "Unit Tests React",
      "test_command": "cd ~/webapp && npm test -- --watchAll=false --coverage",
      "expected": "All tests passed",
      "stop_on_fail": true
    },
    {
      "id": "react_build",
      "type": "bash",
      "priority": 4,
      "prompt": "Esegui npm run build in ~/webapp per produzione"
    },
    {
      "id": "react_verify_build",
      "type": "test",
      "priority": 5,
      "test_name": "Verifica build output",
      "test_command": "ls -la ~/webapp/build/index.html",
      "expected": "index.html"
    },
    {
      "id": "react_size_report",
      "type": "python",
      "priority": 6,
      "prompt": "Analizza ~/webapp/build, calcola dimensione totale e lista i 5 file più grandi, stampa report formattato"
    }
  ]
}
```

### Esempio 3: Backup e Manutenzione Sistema

```json
{
  "tasks": [
    {
      "id": "maint_pre_check",
      "type": "test",
      "priority": 1,
      "test_name": "Verifica spazio disco",
      "test_command": "df -h / | tail -1 | awk '{print $5}' | tr -d '%'",
      "expected": ""
    },
    {
      "id": "maint_backup_home",
      "type": "bash",
      "priority": 2,
      "prompt": "Crea backup compresso di ~/Documents in ~/backups/documents_$(date +%Y%m%d).tar.gz"
    },
    {
      "id": "maint_backup_config",
      "type": "bash",
      "priority": 3,
      "prompt": "Crea backup di ~/panda/config in ~/backups/panda_config_$(date +%Y%m%d).tar.gz"
    },
    {
      "id": "maint_cleanup_temp",
      "type": "bash",
      "priority": 4,
      "prompt": "Elimina file temporanei (.tmp, .bak, ~) più vecchi di 7 giorni in ~"
    },
    {
      "id": "maint_cleanup_cache",
      "type": "bash",
      "priority": 5,
      "prompt": "Pulisci cache apt e rimuovi pacchetti non necessari"
    },
    {
      "id": "maint_cleanup_old_backups",
      "type": "bash",
      "priority": 6,
      "prompt": "Elimina backup più vecchi di 30 giorni in ~/backups"
    },
    {
      "id": "maint_log_rotate",
      "type": "bash",
      "priority": 7,
      "prompt": "Elimina log PANDA più vecchi di 14 giorni in ~/panda/logs"
    },
    {
      "id": "maint_report",
      "type": "python",
      "priority": 8,
      "prompt": "Genera report HTML ~/panda/reports/maintenance_$(date +%Y%m%d).html con: spazio disco usato, numero backup esistenti, data ultimo backup, dimensione cartella panda"
    }
  ]
}
```

### Esempio 4: Generazione Documentazione API

```json
{
  "tasks": [
    {
      "id": "docs_structure",
      "type": "bash",
      "priority": 1,
      "prompt": "Crea struttura ~/docs/api con cartelle: endpoints, models, examples, guides"
    },
    {
      "id": "docs_index",
      "type": "file",
      "priority": 2,
      "filepath": "~/docs/api/index.md",
      "prompt": "Crea indice documentazione API con link a: Introduzione, Autenticazione, Endpoints, Modelli, Esempi"
    },
    {
      "id": "docs_intro",
      "type": "file",
      "priority": 3,
      "filepath": "~/docs/api/guides/introduction.md",
      "prompt": "Scrivi introduzione all'API REST con: overview, base URL, versioning, rate limits, formato risposte"
    },
    {
      "id": "docs_auth",
      "type": "file",
      "priority": 4,
      "filepath": "~/docs/api/guides/authentication.md",
      "prompt": "Documenta autenticazione API con: API keys, JWT tokens, OAuth2, esempi curl per ogni metodo"
    },
    {
      "id": "docs_users_endpoint",
      "type": "file",
      "priority": 5,
      "filepath": "~/docs/api/endpoints/users.md",
      "prompt": "Documenta endpoint /api/users con: GET lista, GET singolo, POST crea, PUT aggiorna, DELETE. Includi parametri, body, response, errori"
    },
    {
      "id": "docs_products_endpoint",
      "type": "file",
      "priority": 6,
      "filepath": "~/docs/api/endpoints/products.md",
      "prompt": "Documenta endpoint /api/products con: GET lista (con filtri, paginazione), GET singolo, POST, PUT, DELETE. Includi esempi"
    },
    {
      "id": "docs_user_model",
      "type": "file",
      "priority": 7,
      "filepath": "~/docs/api/models/user.md",
      "prompt": "Documenta modello User con tutti i campi, tipi, validazioni, relazioni, esempio JSON"
    },
    {
      "id": "docs_product_model",
      "type": "file",
      "priority": 8,
      "filepath": "~/docs/api/models/product.md",
      "prompt": "Documenta modello Product con tutti i campi, tipi, validazioni, relazioni, esempio JSON"
    },
    {
      "id": "docs_examples",
      "type": "file",
      "priority": 9,
      "filepath": "~/docs/api/examples/common_flows.md",
      "prompt": "Crea esempi di flussi comuni: registrazione utente, login, creazione ordine, con sequenza di chiamate API"
    },
    {
      "id": "docs_postman",
      "type": "file",
      "priority": 10,
      "filepath": "~/docs/api/examples/postman_collection.json",
      "prompt": "Crea Postman collection JSON con tutti gli endpoint documentati, variabili ambiente, test automatici"
    }
  ]
}
```

### Esempio 5: Monitoraggio Multi-Servizio

```json
{
  "tasks": [
    {
      "id": "monitor_nginx",
      "type": "test",
      "priority": 1,
      "test_name": "Nginx attivo",
      "test_command": "systemctl is-active nginx",
      "expected": "active"
    },
    {
      "id": "monitor_postgres",
      "type": "test",
      "priority": 2,
      "test_name": "PostgreSQL attivo",
      "test_command": "systemctl is-active postgresql",
      "expected": "active"
    },
    {
      "id": "monitor_redis",
      "type": "test",
      "priority": 3,
      "test_name": "Redis attivo",
      "test_command": "systemctl is-active redis",
      "expected": "active"
    },
    {
      "id": "monitor_app",
      "type": "test",
      "priority": 4,
      "test_name": "App risponde",
      "test_command": "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health",
      "expected": "200"
    },
    {
      "id": "monitor_disk",
      "type": "python",
      "priority": 5,
      "prompt": "Controlla uso disco di /, /var, /home. Se qualcuno > 80%, stampa WARNING. Stampa riepilogo"
    },
    {
      "id": "monitor_memory",
      "type": "python",
      "priority": 6,
      "prompt": "Controlla uso RAM con psutil. Se > 90%, stampa CRITICAL. Stampa uso attuale in GB"
    },
    {
      "id": "monitor_report",
      "type": "file",
      "priority": 7,
      "filepath": "~/monitoring/status_$(date +%Y%m%d_%H%M%S).json",
      "prompt": "Genera report JSON con: timestamp, stato servizi (nginx, postgres, redis, app), uso disco per partizione, uso RAM"
    }
  ]
}
```

---

## Validazione del JSON

### Validazione Manuale

Prima di importare, valida il JSON:

```bash
# Con Python
python3 -m json.tool tasks.json > /dev/null && echo "JSON valido" || echo "JSON non valido"

# Con jq
jq '.' tasks.json > /dev/null && echo "JSON valido" || echo "JSON non valido"
```

### Script di Validazione Completo

```python
#!/usr/bin/env python3
"""
validate_tasks.py - Validatore JSON per import PANDA

Uso: python3 validate_tasks.py <file.json>
"""

import json
import sys
from typing import Dict, List

VALID_TYPES = ["prompt", "bash", "python", "file", "test", "multi"]

def validate_task(task: Dict, index: int) -> List[str]:
    """Valida singolo task, ritorna lista errori."""
    errors = []
    task_id = task.get("id", f"task[{index}]")

    # Tipo richiesto
    if "type" not in task:
        errors.append(f"{task_id}: campo 'type' mancante")
    elif task["type"] not in VALID_TYPES:
        errors.append(f"{task_id}: tipo '{task['type']}' non valido (validi: {VALID_TYPES})")

    task_type = task.get("type", "")

    # Validazioni per tipo
    if task_type in ["prompt", "bash", "python"]:
        if "prompt" not in task or not task["prompt"].strip():
            errors.append(f"{task_id}: campo 'prompt' richiesto e non vuoto per tipo '{task_type}'")

    if task_type == "file":
        if "prompt" not in task:
            errors.append(f"{task_id}: campo 'prompt' richiesto per tipo 'file'")
        if "filepath" not in task:
            errors.append(f"{task_id}: campo 'filepath' richiesto per tipo 'file'")

    if task_type == "test":
        if "test_command" not in task:
            errors.append(f"{task_id}: campo 'test_command' richiesto per tipo 'test'")

    if task_type == "multi":
        if "steps" not in task:
            errors.append(f"{task_id}: campo 'steps' richiesto per tipo 'multi'")
        elif not isinstance(task["steps"], list):
            errors.append(f"{task_id}: 'steps' deve essere un array")
        elif len(task["steps"]) == 0:
            errors.append(f"{task_id}: 'steps' non può essere vuoto")
        else:
            # Valida ricorsivamente ogni step
            for i, step in enumerate(task["steps"]):
                step_errors = validate_task(step, i)
                for err in step_errors:
                    errors.append(f"{task_id}.steps[{i}]: {err.split(': ', 1)[-1]}")

    # Validazione priority
    if "priority" in task:
        if not isinstance(task["priority"], int):
            errors.append(f"{task_id}: 'priority' deve essere intero")
        elif task["priority"] < 1:
            errors.append(f"{task_id}: 'priority' deve essere >= 1")

    # Warning per campi sospetti
    known_fields = {"id", "type", "priority", "prompt", "prompt_file", "filepath",
                    "test_name", "test_command", "expected", "steps", "stop_on_fail", "_retry"}
    for field in task:
        if field not in known_fields:
            errors.append(f"{task_id}: campo sconosciuto '{field}' (potrebbe essere ignorato)")

    return errors

def validate_file(filepath: str) -> bool:
    """Valida file JSON per import PANDA."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERRORE: File '{filepath}' non trovato")
        return False
    except json.JSONDecodeError as e:
        print(f"ERRORE: JSON non valido - {e}")
        return False

    # Verifica struttura root
    if "tasks" not in data:
        print("ERRORE: Chiave 'tasks' mancante nel JSON root")
        return False

    if not isinstance(data["tasks"], list):
        print("ERRORE: 'tasks' deve essere un array")
        return False

    if len(data["tasks"]) == 0:
        print("WARNING: Array 'tasks' vuoto")
        return True

    # Valida ogni task
    all_errors = []
    for i, task in enumerate(data["tasks"]):
        errors = validate_task(task, i)
        all_errors.extend(errors)

    # Report
    if all_errors:
        print(f"Trovati {len(all_errors)} problemi:\n")
        for err in all_errors:
            print(f"  - {err}")
        print()
        return False
    else:
        print(f"OK: {len(data['tasks'])} task validi")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <file.json>")
        sys.exit(1)

    success = validate_file(sys.argv[1])
    sys.exit(0 if success else 1)
```

### Validazione Online

Puoi usare servizi online come:
- https://jsonlint.com
- https://jsonformatter.org

Ma ricorda: validano solo la sintassi JSON, non la struttura specifica PANDA.

---

## Gestione degli Errori

### Errori Comuni e Soluzioni

#### Errore: "JSON non valido"

**Causa**: Sintassi JSON errata

**Diagnosi**:
```bash
python3 -m json.tool tasks.json
```

**Soluzioni comuni**:
- Usa virgolette doppie `"`, non singole `'`
- Rimuovi virgola dopo ultimo elemento array
- Verifica parentesi bilanciate

#### Errore: "tasks field missing"

**Causa**: Il JSON non ha la chiave `tasks`

**Soluzione**: La struttura deve essere:
```json
{
  "tasks": [...]
}
```

Non:
```json
[...]
```

#### Errore: Task importati ma falliscono

**Causa**: Task validi come JSON ma con dati errati per PANDA

**Diagnosi**:
```bash
# Vedi risultato ultimo task
cat ~/panda/results/TASKID_*.json
```

**Soluzioni**:
- Verifica che `type` sia valido
- Per `file`, verifica `filepath` presente
- Per `test`, verifica `test_command` presente

### Errori di Rete

#### Connection refused

```bash
curl: (7) Failed to connect to localhost port 5000: Connection refused
```

**Causa**: Dashboard non in esecuzione

**Soluzione**:
```bash
sudo systemctl start panda-dashboard
```

#### Timeout

**Causa**: Import molto grande o server sovraccarico

**Soluzione**:
```bash
# Aumenta timeout cURL
curl --max-time 120 -X POST ...

# O dividi in batch più piccoli
```

### Recupero da Import Parziale

Se l'import fallisce a metà, alcuni task potrebbero essere già stati creati:

```bash
# Vedi task creati di recente
ls -lt ~/panda/tasks/*.json | head -20

# Per annullare, elimina i file
rm ~/panda/tasks/task_TIMESTAMP_*.json
```

---

## Best Practices

### 1. Sempre Validare Prima di Import

```bash
# Valida JSON
python3 -m json.tool tasks.json > /dev/null

# Poi importa
curl -X POST ... -d @tasks.json
```

### 2. Usa ID Descrittivi

```json
// Buono
{"id": "backup_daily_database", ...}

// Cattivo
{"id": "task1", ...}
```

### 3. Documenta i Task

Aggiungi commenti nei prompt per chiarezza:

```json
{
  "id": "setup_nginx",
  "type": "bash",
  "prompt": "Configura nginx come reverse proxy per app su porta 3000. [NOTA: richiede sudo]"
}
```

### 4. Testa con Pochi Task Prima

Prima di importare 100 task, testa con 2-3:

```json
{
  "tasks": [
    {"id": "test_1", "type": "bash", "priority": 1, "prompt": "echo test1"},
    {"id": "test_2", "type": "bash", "priority": 2, "prompt": "echo test2"}
  ]
}
```

### 5. Versionizza i JSON

Salva i file JSON in git per:
- Storico modifiche
- Collaborazione team
- Rollback se necessario

### 6. Usa Priorità Significative

```json
// Pipeline con fasi chiare
Priority 1-10:   Setup/Prerequisiti
Priority 11-20:  Build
Priority 21-30:  Test
Priority 31-40:  Deploy
Priority 41-50:  Cleanup/Report
```

### 7. Gestisci i Fallimenti

Usa `stop_on_fail` per task critici:

```json
{
  "id": "critical_backup",
  "type": "bash",
  "prompt": "...",
  "stop_on_fail": true
}
```

### 8. Monitora l'Esecuzione

Dopo l'import, controlla:

```bash
# Coda
curl http://localhost:5000/api/tasks/pending | jq '. | length'

# Log
tail -f ~/panda/logs/$(date +%Y-%m-%d).log
```

---

## Casi d'Uso Avanzati

### Import Condizionale

Script che importa task solo se certe condizioni sono soddisfatte:

```bash
#!/bin/bash

# Importa task di deploy solo se i test passano
TEST_RESULT=$(curl -s http://localhost:5000/api/results | jq -r '.[0].success')

if [ "$TEST_RESULT" = "true" ]; then
    curl -X POST http://localhost:5000/api/tasks/import \
        -H "Content-Type: application/json" \
        -d @deploy_tasks.json
    echo "Deploy task importati"
else
    echo "Test falliti, deploy non eseguito"
fi
```

### Import Schedulato con Cron

```cron
# Backup giornaliero alle 2:00
0 2 * * * curl -X POST http://localhost:5000/api/tasks/import -H "Content-Type: application/json" -d @/home/user/panda_tasks/daily_backup.json

# Manutenzione settimanale domenica alle 3:00
0 3 * * 0 curl -X POST http://localhost:5000/api/tasks/import -H "Content-Type: application/json" -d @/home/user/panda_tasks/weekly_maintenance.json
```

### Import da Webhook

Script Flask per ricevere webhook e importare task:

```python
from flask import Flask, request
import requests

app = Flask(__name__)
PANDA_URL = "http://localhost:5000"

@app.route('/webhook/github', methods=['POST'])
def github_webhook():
    data = request.json

    if data.get('action') == 'push':
        # Import task di build su push
        tasks = {
            "tasks": [
                {"id": "build_on_push", "type": "bash", "priority": 1,
                 "prompt": f"Build progetto dopo push su branch {data.get('ref')}"}
            ]
        }
        requests.post(f"{PANDA_URL}/api/tasks/import", json=tasks)
        return "Build task queued", 200

    return "OK", 200

if __name__ == '__main__':
    app.run(port=5001)
```

### Generazione Task da Database

```python
import sqlite3
import requests

def tasks_from_database():
    """Genera task da record database."""
    conn = sqlite3.connect('pending_operations.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, operation, target FROM pending_ops WHERE status='new'")
    rows = cursor.fetchall()

    tasks = []
    for i, (op_id, operation, target) in enumerate(rows, start=1):
        tasks.append({
            "id": f"db_op_{op_id}",
            "type": "bash",
            "priority": i,
            "prompt": f"Esegui operazione '{operation}' su '{target}'"
        })

    conn.close()

    if tasks:
        response = requests.post(
            "http://localhost:5000/api/tasks/import",
            json={"tasks": tasks}
        )
        return response.json()
    return {"imported": 0}
```

### Import con Template Jinja2

```python
from jinja2 import Template
import json
import requests

# Template per task ripetitivi
TEMPLATE = """
{
  "tasks": [
    {% for item in items %}
    {
      "id": "process_{{ item.id }}",
      "type": "{{ task_type }}",
      "priority": {{ loop.index }},
      "prompt": "{{ prompt_template.format(**item) }}"
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
"""

# Dati
items = [
    {"id": "report_1", "name": "Report Vendite", "format": "PDF"},
    {"id": "report_2", "name": "Report Marketing", "format": "Excel"},
    {"id": "report_3", "name": "Report HR", "format": "PDF"},
]

# Genera JSON
template = Template(TEMPLATE)
json_str = template.render(
    items=items,
    task_type="python",
    prompt_template="Genera {name} in formato {format}"
)

# Importa
data = json.loads(json_str)
response = requests.post(
    "http://localhost:5000/api/tasks/import",
    json=data
)
print(f"Importati {response.json()['imported']} task")
```

---

## Script di Utilità

### import_and_wait.py

Script che importa e attende completamento:

```python
#!/usr/bin/env python3
"""
Import task e attendi completamento.

Uso: python3 import_and_wait.py tasks.json [timeout_minuti]
"""

import sys
import time
import json
import requests

PANDA_URL = "http://localhost:5000"

def import_tasks(filepath):
    with open(filepath) as f:
        data = json.load(f)

    response = requests.post(f"{PANDA_URL}/api/tasks/import", json=data)
    return response.json()

def get_pending_count():
    response = requests.get(f"{PANDA_URL}/api/tasks/pending")
    return len(response.json())

def wait_completion(timeout_minutes=30):
    start = time.time()
    timeout_seconds = timeout_minutes * 60

    while time.time() - start < timeout_seconds:
        pending = get_pending_count()
        if pending == 0:
            return True
        print(f"In attesa... {pending} task rimanenti")
        time.sleep(10)

    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <file.json> [timeout_minuti]")
        sys.exit(1)

    filepath = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # Import
    print(f"Importando task da {filepath}...")
    result = import_tasks(filepath)

    if not result.get("success"):
        print(f"Errore import: {result}")
        sys.exit(1)

    print(f"Importati {result['imported']} task")

    # Attendi
    print(f"Attendo completamento (timeout: {timeout} minuti)...")
    if wait_completion(timeout):
        print("Tutti i task completati!")
    else:
        print("Timeout raggiunto, alcuni task ancora in coda")
        sys.exit(1)
```

### batch_import.sh

Script per import di multipli file:

```bash
#!/bin/bash
# batch_import.sh - Importa tutti i JSON da una directory

PANDA_URL="${PANDA_URL:-http://localhost:5000}"
DIR="${1:-.}"

echo "Importando task da $DIR..."

for file in "$DIR"/*.json; do
    if [ -f "$file" ]; then
        echo "  Importando $file..."
        result=$(curl -s -X POST "$PANDA_URL/api/tasks/import" \
            -H "Content-Type: application/json" \
            -d @"$file")
        imported=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('imported',0))")
        echo "    -> $imported task importati"
    fi
done

echo "Fatto!"
```

### convert_csv_to_json.py

Converti CSV in JSON per import:

```python
#!/usr/bin/env python3
"""
Converte CSV in JSON per import PANDA.

CSV deve avere colonne: id,type,priority,prompt[,filepath]

Uso: python3 convert_csv_to_json.py input.csv output.json
"""

import csv
import json
import sys

def csv_to_tasks(csv_path):
    tasks = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            task = {
                "id": row["id"],
                "type": row["type"],
                "priority": int(row.get("priority", 10)),
                "prompt": row["prompt"]
            }
            if row.get("filepath"):
                task["filepath"] = row["filepath"]
            if row.get("test_command"):
                task["test_command"] = row["test_command"]
            if row.get("expected"):
                task["expected"] = row["expected"]
            tasks.append(task)
    return {"tasks": tasks}

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <input.csv> <output.json>")
        sys.exit(1)

    data = csv_to_tasks(sys.argv[1])

    with open(sys.argv[2], 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Convertiti {len(data['tasks'])} task in {sys.argv[2]}")
```

Esempio CSV (`tasks.csv`):
```csv
id,type,priority,prompt,filepath
task1,bash,1,Elenca file,
task2,file,2,Crea script hello,~/hello.py
task3,python,3,Stampa data,
```

---

## Troubleshooting Import

### Problema: Import lento

**Sintomo**: Import di molti task impiega molto tempo

**Causa**: Delay di 10ms tra task + scrittura file

**Soluzioni**:
- Importa in batch più piccoli
- Usa import parallelo (non consigliato, rischio collisioni)

### Problema: Task duplicati

**Sintomo**: Stesso task appare più volte

**Causa**: Re-import dello stesso file

**Soluzione**: Usa ID univoci o verifica prima dell'import:

```python
pending = requests.get(f"{PANDA_URL}/api/tasks/pending").json()
existing_ids = {t["id"] for t in pending}

tasks_to_import = [t for t in tasks if t.get("id") not in existing_ids]
```

### Problema: Caratteri speciali nel prompt

**Sintomo**: JSON non valido con caratteri speciali

**Causa**: Caratteri non escaped

**Soluzione**: Usa escape appropriato:
```python
import json
prompt = 'Testo con "virgolette" e\nnewline'
safe_prompt = json.dumps(prompt)[1:-1]  # Rimuove virgolette esterne
```

### Problema: Filepath non espanso

**Sintomo**: File creato in path sbagliato

**Causa**: `~` non espanso da PANDA

**Soluzione**: PANDA espande `~` automaticamente. Verifica che il path sia scritto correttamente:
```json
"filepath": "~/panda/output/file.txt"  // Corretto
"filepath": "~panda/output/file.txt"   // Sbagliato (manca /)
```

---

## FAQ - Domande Frequenti

### Q: Quanti task posso importare in una volta?

**A**: Non c'è un limite hard-coded. Abbiamo testato con successo fino a 1000 task. Per import più grandi, considera di dividere in batch da 100-200.

### Q: Posso importare task mentre altri sono in esecuzione?

**A**: Sì! I nuovi task vengono aggiunti alla coda e verranno processati secondo la loro priorità.

### Q: Come annullo un import?

**A**: Elimina i file dalla directory tasks:
```bash
rm ~/panda/tasks/task_TIMESTAMP_*.json
```

### Q: Posso usare CSV invece di JSON?

**A**: Non direttamente, ma puoi convertire CSV in JSON con lo script fornito nella sezione [Script di Utilità](#script-di-utilità).

### Q: I task vengono eseguiti nell'ordine in cui li metto nel JSON?

**A**: Solo se hanno tutti la stessa priorità. Altrimenti, la priorità determina l'ordine (numeri più bassi prima).

### Q: Cosa succede se un task nell'import ha lo stesso ID di uno esistente?

**A**: Viene creato un nuovo file con timestamp diverso. Potresti avere due task con lo stesso ID ma filename diverso.

### Q: Posso importare task di tipo `multi` con step annidati?

**A**: Sì, ma solo un livello di annidamento. Gli step non possono contenere altri step.

### Q: Come faccio debug di un import fallito?

**A**:
1. Valida il JSON: `python3 -m json.tool tasks.json`
2. Controlla log PANDA: `tail ~/panda/logs/$(date +%Y-%m-%d).log`
3. Verifica risultati: `ls -t ~/panda/results/*.json | head -5 | xargs cat`

### Q: L'import è atomico?

**A**: No. Se l'import fallisce a metà, i task già creati rimarranno. Per cleanup, elimina manualmente i file.

### Q: Posso programmare import ricorrenti?

**A**: Sì, usa cron o systemd timer. Vedi la sezione [Import Schedulato con Cron](#import-schedulato-con-cron).

---

## Conclusione

L'import massivo è una funzionalità potente che permette di automatizzare workflow complessi con PANDA. Ricapitolando:

1. **Prepara il JSON** con la struttura corretta
2. **Valida sempre** prima di importare
3. **Scegli il metodo** più adatto (Dashboard, cURL, Python)
4. **Usa priorità** per controllare l'ordine
5. **Monitora** l'esecuzione dopo l'import
6. **Gestisci errori** con `stop_on_fail` dove serve

Per domande o problemi, consulta la [documentazione principale](doc.md) o i log in `~/panda/logs/`.

---

*Guida Import Massivo PANDA v1.0 - Gennaio 2026*
