Certo! Ecco uno script Python che esegue le operazioni richieste:

```python
import os
import re

def remove_before_first_code(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Ricerca la prima linea di codice (riga che inizia con import, def o <!DOCTYPE)
    pattern = r'^(import\s+|def\s+\w+\s*\(|<!DOCTYPE\b).*$'
    first_code_line_index = next((i for i, line in enumerate(content.split('\n')) if re.match(pattern, line)), None)

    if first_code_line_index is not None:
        # Rimuovi tutto ciò che precede la prima linea di codice
        content = '\n'.join(content.split('\n')[first_code_line_index:])

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_name.endswith('.py') or file_name.endswith('.html'):
                file_path = os.path.join(root, file_name)
                print(f"Processing {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                    # Controlla se il file contiene le stringhe 'Certamente' o 'Ecco il codice'
                    if 'Certamente' in content or 'Ecco il codice' in content:
                        remove_before_first_code(file_path)
                        print(f"Processed and updated {file_path}")

if __name__ == "__main__":
    directory = os.path.expanduser("~/panda/projects")
    process_directory(directory)
```

### Spiegazione del Codice:

1. **remove_before_first_code(file_path):**
   - Questa funzione legge il contenuto del file specificato.
   - Utilizza una regex per trovare la prima linea di codice (che inizia con `import`, `def`, o `<!DOCTYPE`).
   - Rimuove tutto ciò che precede questa linea e salva il file modificato.

2. **process_directory(directory):**
   - Questa funzione cammina attraverso tutti i file nella directory specificata (`~/panda/projects`).
   - Controlla se il file termina con `.py` o `.html`.
   - Se contiene le stringhe 'Certamente' o 'Ecco il codice', chiama la funzione `remove_before_first_code`.

3. **main:**
   - Espande il percorso della directory home dell'utente e inizia a processare i file nella directory specificata.

### Come Funziona:
- Il script scorre tutti i file `.py` e `.html` nella directory `~/panda/projects`.
- Per ogni file che contiene le stringhe 'Certamente' o 'Ecco il codice', elimina tutto ciò che precede la prima linea di codice reale.
- Salva i file modificati.

### Nota:
Assicurati di avere i permessi necessari per leggere e scrivere nei file nella directory specificata. Se esistono file lock o altri problemi di permesso, potrebbe essere necessario gestire questi casi in modo appropriato.