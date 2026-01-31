html
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cerca Eventi</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        .container {
            width: 80%;
            margin: 0 auto;
        }
        .search-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .search-input, .category-select {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        .search-button {
            padding: 10px 20px;
            background-color: #007BFF;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .event-list {
            list-style-type: none;
            padding: 0;
        }
        .event-item {
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .loading, .error {
            text-align: center;
            color: red;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="search-bar">
            <input type="text" id="q" placeholder="Cerca evento...">
            <select id="city">
                <option value="">Seleziona città</option>
                <!-- Opzioni delle città dinamiche -->
            </select>
            <select id="category">
                <option value="">Seleziona categoria</option>
                <!-- Opzioni delle categorie dinamiche -->
            </select>
            <button class="search-button" onclick="searchEvents()">Cerca</button>
        </div>
        <ul class="event-list" id="eventList"></ul>
        <div class="loading" id="loading">Caricamento in corso...</div>
        <div class="error" id="error"></div>
    </div>

    <script>
        async function searchEvents() {
            const q = document.getElementById('q').value;
            const city = document.getElementById('city').value;
            const category = document.getElementById('category').value;

            try {
                const response = await fetch(`/api/events?q=${q}&city=${city}&category=${category}`);
                if (!response.ok) {
                    throw new Error('Errore nel caricare gli eventi');
                }
                const events = await response.json();
                displayEvents(events);
            } catch (error) {
                handleError(error.message);
            }
        }

        function displayEvents(events) {
            const eventList = document.getElementById('eventList');
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');

            eventList.innerHTML = '';
            loading.style.display = 'none';
            error.style.display = 'none';

            if (events.length === 0) {
                eventList.innerHTML = '<li>Nessun evento trovato</li>';
            } else {
                events.forEach(event => {
                    const eventItem = document.createElement('li');
                    eventItem.classList.add('event-item');
                    eventItem.innerHTML = `
                        <a href="/detail?id=${event.id}" target="_blank">${event.title}</a>
                        <p>Città: ${event.city}</p>
                        <p>Categoria: ${event.category}</p>
                    `;
                    eventList.appendChild(eventItem);
                });
            }
        }

        function handleError(message) {
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');

            loading.style.display = 'none';
            error.textContent = message;
            error.style.display = 'block';
        }

        // Carica dinamicamente le città e le categorie
        async function loadOptions() {
            try {
                const response = await fetch('/api/options');
                if (!response.ok) {
                    throw new Error('Errore nel caricare le opzioni');
                }
                const options = await response.json();

                const citySelect = document.getElementById('city');
                const categorySelect = document.getElementById('category');

                options.cities.forEach(city => {
                    const option = document.createElement('option');
                    option.value = city;
                    option.textContent = city;
                    citySelect.appendChild(option);
                });

                options.categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categorySelect.appendChild(option);
                });
            } catch (error) {
                handleError(error.message);
            }
        }

        loadOptions();
    </script>
</body>
</html>