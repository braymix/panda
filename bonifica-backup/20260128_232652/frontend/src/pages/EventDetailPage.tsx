Ecco un esempio di codice per una pagina di dettaglio evento utilizzando React, Node.js e Express:

```javascript
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

// Importa il layout
import Layout from './Layout';

const EventDetail = () => {
  const [event, setEvent] = useState(null);
  const { id } = useParams();

  useEffect(() => {
    const fetchEvent = async () => {
      try {
        const response = await axios.get(`https://api.example.com/events/${id}`);
        setEvent(response.data);
      } catch (error) {
        console.error('Errore durante il recupero dell\'evento:', error);
      }
    };

    fetchEvent();
  }, [id]);

  if (!event) {
    return <div>Caricando...</div>;
  }

  const { name, date, location, description } = event;

  return (
    <Layout>
      <h1>{name}</h1>
      <p><strong>Data:</strong> {date}</p>
      <p><strong>Luogo:</strong> {location}</p>
      <div dangerouslySetInnerHTML={{ __html: description }}></div>

      {/* Link back al listino eventi */}
      <a href="/events" className="back-link">Torna ai Eventi</a>
    </Layout>
  );
};

export default EventDetail;
```

### Spiegazione del codice:

1. **`useParams`:** Utilizza `useParams` per leggere l'ID dell'evento dalla route params (`/events/:id`).

2. **`useEffect`:** Quando il componente monta o cambia, effettua una chiamata API per recuperare i dettagli dell'evento.

3. **Layout:** Utilizza il layout importato per racchiudere il contenuto della pagina.

4. **Rendering:** Mostra i campi di nome, data, luogo e descrizione dell'evento. La descrizione è mostrata come HTML usando `dangerouslySetInnerHTML` per accettare input formattati in HTML.

5. **Link back:** Inserisce un link che permette all'utente di tornare alla lista degli eventi.

### Note:

- Assicurati di sostituire l'URL dell'API (`https://api.example.com/events/${id}`) con la tua API reale.
- Assicurati di avere configurato `react-router-dom` per gestire le routes correttamente.
- Il layout (`Layout`) deve essere implementato in un file separato e importato nel componente principale.

Questo codice fornisce una struttura di base per una pagina di dettaglio evento, utilizzando React per la logica del componente e un layout personalizzato.