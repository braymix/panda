Ecco un esempio di codice HTML per una pagina di creazione evento con i campi richiesti e un layout semplice:

```html
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crea Evento</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .container {
            max-width: 600px;
            margin: auto;
            padding: 20px;
            background-color: #f4f4f9;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"],
        input[type="number"],
        select,
        textarea {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>

<div class="container">
    <h2>Crea Evento</h2>
    <form id="eventForm" action="/createEvent" method="POST">
        <div class="form-group">
            <label for="title">Titolo:</label>
            <input type="text" id="title" name="title" required>
        </div>
        <div class="form-group">
            <label for="description">Descrizione:</label>
            <textarea id="description" name="description" rows="4" required></textarea>
        </div>
        <div class="form-group">
            <label for="city">Città:</label>
            <input type="text" id="city" name="city" required>
        </div>
        <div class="form-group">
            <label for="venue">Luogo:</label>
            <input type="text" id="venue" name="venue" required>
        </div>
        <div class="form-group">
            <label for="category">Categoria:</label>
            <select id="category" name="category" required>
                <option value="">Seleziona</option>
                <option value="Conferenza">Conferenza</option>
                <option value="Workshop">Workshop</option>
                <option value="Festival">Festival</option>
                <!-- Aggiungi altre categorie se necessario -->
            </select>
        </div>
        <div class="form-group">
            <label for="startAt">Data e ora inizio:</label>
            <input type="datetime-local" id="startAt" name="startAt" required>
        </div>
        <div class="form-group">
            <label for="endAt">Data e ora fine:</label>
            <input type="datetime-local" id="endAt" name="endAt" required>
        </div>
        <div class="form-group">
            <label for="organizer">Organizzatore:</label>
            <input type="text" id="organizer" name="organizer" required>
        </div>
        <div class="form-group">
            <label for="price">Prezzo:</label>
            <input type="number" id="price" name="price" step="0.01" required>
        </div>
        <div class="form-group">
            <label for="url">URL evento:</label>
            <input type="text" id="url" name="url" required>
        </div>
        <button type="submit">Crea Evento</button>
    </form>

    <div id="error-message" style="color: red; margin-top: 15px;"></div>
</div>

<script>
    document.getElementById('eventForm').addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(this);
        
        fetch('/createEvent', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = `/event/${data.eventId}`;
            } else {
                document.getElementById('error-message').innerText = data.message;
            }
        })
        .catch(error => {
            console.error('Errore durante la creazione dell\'evento:', error);
            document.getElementById('error-message').innerText = 'Si è verificato un errore. Riprova più tardi.';
        });
    });
</script>

</body>
</html>
```

Questo codice crea una pagina semplice con un form per inserire i dati dell'evento. Quando il bottone "Crea Evento" viene premuto, i dati del form vengono inviati tramite una richiesta POST al server. Il JavaScript gestisce la risposta e in caso di successo, reindirizza l'utente alla pagina di dettaglio dell'evento.

Per gestire gli errori, il codice inserisce un messaggio di errore nella pagina se la richiesta non viene completata con successo.