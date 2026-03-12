# ReDirect

ReDirect is an AI-driven traffic optimization prototype designed to help traffic control centers create faster emergency corridors while maintaining smooth traffic flow across major intersections.

The system combines intelligent congestion prediction, adaptive signal control, and emergency vehicle priority routing to improve response times for ambulances, police, and fire services.

---

## Core Features

### Emergency Priority Routing
Emergency vehicles can request traffic clearance through a dedicated portal.  
The system generates optimized signal corridors to ensure faster and safer movement.

### AI-Based Traffic Optimization
ReDirect simulates AI-assisted congestion prediction and traffic density analysis to recommend better signal timings at busy intersections.

### Emergency Traffic API
A structured backend API provides traffic snapshots and emergency request tracking, making the system easy to integrate with operator dashboards.

### Operator Dashboard
The frontend provides a simple portal for traffic operators with:

- Live signal priority status cards
- Emergency request submission form
- Corridor confirmation timeline
- Real-time traffic pressure indicators

### Edge-Friendly Processing
Instead of relying on heavy video pipelines, the system demonstrates how lightweight vehicle metadata from edge devices can be processed and summarized efficiently.

---

## Improvements in This Version

### Frontend

The React portal now includes:

- cleaner dashboard layout
- live signal-priority cards
- improved emergency request workflow
- built-in preview route for quick demonstration

### Backend

The FastAPI backend now provides:

- structured request schemas
- dashboard snapshot endpoint
- emergency request lifecycle tracking
- automatic cleanup for expired requests
- environment-based API key configuration

### Repository Cleanup

The repository is now lighter and cleaner:

- generated files removed
- `.env` files excluded
- local databases removed
- caches and `node_modules` ignored

---

## Project Structure

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

---

## Running the Project Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Backend will run at:

```
http://localhost:8000
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at:

```
http://localhost:5173
```

---

## Preview and API Docs

Preview served by backend:

```
http://localhost:8000/preview
```

API documentation:

```
http://localhost:8000/docs
```

---

## Core API Endpoints

- `GET /health`
- `GET /preview`
- `GET /api/v1/dashboard`
- `POST /api/v1/emergency/requests`
- `GET /api/v1/emergency/requests`
- `GET /api/v1/gov/emergency/active`
- `POST /api/v1/emergency/alert`

---

## Prototype Notes

- The backend uses an in-memory store to keep the prototype lightweight and easy to run.
- Signal recommendations are based on simulated vehicle counts and traffic density scoring.
- AI and edge modules demonstrate how vehicle metadata could be summarized before reaching the central traffic control system.

---

## Documentation

- [Government evaluation notes](docs/government_evaluation.md)
- [Project proposal](docs/samadhan_saathi_proposal.md)
