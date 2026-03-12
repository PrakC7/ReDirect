# ReDirect

ReDirect is a smart traffic optimization prototype focused on one clear use case:
helping control rooms create faster emergency corridors while still showing live
traffic pressure across important intersections.

The project keeps the original concept intact:
- adaptive signal timing for congested junctions
- emergency priority routing for ambulances, police, and fire services
- edge-friendly traffic metadata instead of heavy full-video pipelines
- a simple dashboard-style UI for operators

## What is improved

- The frontend is now a cleaner React portal with:
  - live signal-priority cards
  - an operator-friendly emergency request form
  - a confirmation timeline generated from backend corridor steps
- The backend is now a simpler FastAPI prototype with:
  - structured request schemas
  - a dashboard snapshot endpoint
  - in-memory emergency request tracking with TTL cleanup
  - env-based API key configuration instead of hard-coded secrets
- The repository is lighter:
  - generated files, local databases, `.env`, caches, and `node_modules` are no longer tracked

## Project structure

```text
.
|-- ai
|   `-- detection.py
|-- backend
|   |-- app
|   |   |-- api
|   |   |   `-- routes.py
|   |   |-- core
|   |   |   `-- config.py
|   |   |-- db
|   |   |   `-- models.py
|   |   |-- services
|   |   |   |-- density.py
|   |   |   |-- emergency.py
|   |   |   `-- optimization.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- .env.example
|   |-- requirements.txt
|   `-- run.py
|-- docs
|-- edge
|   `-- edge_processor.py
|-- frontend
|   |-- src
|   |   |-- App.jsx
|   |   |-- api.js
|   |   |-- main.jsx
|   |   `-- styles.css
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
`-- README.md
```

## Local run

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

## Core API endpoints

- `GET /health`
- `GET /api/v1/dashboard`
- `POST /api/v1/emergency/requests`
- `GET /api/v1/emergency/requests`
- `GET /api/v1/gov/emergency/active`
- `POST /api/v1/emergency/alert`

## Prototype notes

- The backend currently uses an in-memory store so the demo stays simple and easy
  to run.
- Signal recommendations are based on simulated live counts, density scoring, and
  priority weighting.
- The AI and edge modules are lightweight helpers that show how vehicle metadata
  could be summarized before reaching the control backend.

## Docs

- [Government evaluation notes](docs/government_evaluation.md)
- [Project proposal](docs/samadhan_saathi_proposal.md)
