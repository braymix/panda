# Events App (Event Finder)

Progetto full-stack per cercare e gestire eventi.

## Stack
- Backend: Java 21, Spring Boot 3, JPA, Validation, Flyway, OpenAPI
- DB: PostgreSQL
- Frontend: React + Vite + TypeScript
- Ops: Docker Compose

## Avvio rapido con Docker

```bash
cd ops
docker compose up --build
```

- Backend: http://localhost:8080
- OpenAPI: http://localhost:8080/swagger-ui.html
- Frontend: http://localhost:5173

## Variabili ambiente (Docker)
Backend usa:
- SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/events
- SPRING_DATASOURCE_USERNAME=events
- SPRING_DATASOURCE_PASSWORD=events

## Dev locale
### Backend
```bash
cd backend
mvn test
mvn spring-boot:run
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API principali
- GET /api/events?q=&from=&to=&city=&category=&page=&size=
- GET /api/events/{id}
- POST /api/events
- PUT /api/events/{id}
- DELETE /api/events/{id}