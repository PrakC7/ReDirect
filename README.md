# ReDirect – AI Powered Smart Traffic Optimization System

## System Overview
ReDirect is a practical, scalable traffic management prototype for Municipal Corporation of Delhi. It ingests live vehicle counts from existing camera feeds, calculates density using road characteristics and historical congestion, optimizes green times every 30 seconds, and prioritizes emergency corridors.

## Architecture Diagram
```mermaid
flowchart LR
    Cameras[Traffic Cameras] --> Edge[Edge Processing Node]
    Maps[External Traffic Data] --> Regional[Regional Server]
    Edge --> Regional
    Regional --> Central[Central Control Server]
    Central --> Dashboard[Monitoring Dashboard]
    Central --> Signals[Signal Control System]
    Emergency[Emergency Portal] --> Central
```

## Project Folder Structure
```
.
├── ai
│   ├── detection.py
│   └── requirements.txt
├── backend
│   ├── app
│   │   ├── api
│   │   │   └── routes.py
│   │   ├── core
│   │   │   └── config.py
│   │   ├── db
│   │   │   ├── models.py
│   │   │   ├── schema.sql
│   │   │   └── session.py
│   │   ├── services
│   │   │   ├── density.py
│   │   │   ├── emergency.py
│   │   │   └── optimization.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── sample_data
│   │   └── seed.sql
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── edge
│   ├── edge_config.json
│   ├── edge_processor.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## Backend Implementation
- FastAPI service with traffic ingest, intersection registry, signal plan generation, and emergency corridor activation.
- PostgreSQL schema aligned with real-time monitoring and historical storage.

## AI Detection Code
- YOLOv8 inference using OpenCV.
- Outputs vehicle_count, vehicle_type_distribution, emergency_detected.

## Traffic Optimization Algorithm
- Density score uses vehicle count, lane count, road width, priority weight, and historical congestion.
- Queue-based prioritization assigns green times between 20s and 90s.
- Signal updates supported every 30 seconds.

## Emergency Corridor Logic
- Supports vision-based emergency detection and portal submissions.
- Generates sequential green windows across intersections.

## React Dashboard
- Government-style interface with live density status, signal plans, emergency routes, and camera feed placeholders.

## Database Schema
See [schema.sql](file:///d:/Projects/prototype/backend/app/db/schema.sql).

## Deployment Guide
1. Install Docker and Docker Compose.
2. Run `docker compose up --build`.
3. Load sample intersections with `backend/sample_data/seed.sql`.
4. Access dashboard at `http://localhost:5173`.
5. Access API at `http://localhost:8000/docs`.

## Future Scalability Plan
- Edge nodes for intersections and corridor detection.
- Regional aggregation servers for zone-level optimization.
- Central command for citywide monitoring and policy control.

## Emergency Traffic Priority Request Portal – User Flow

```mermaid
flowchart LR
    subgraph Portal["Emergency Traffic Priority Request Portal"]
      A["Landing Page\n- Title\n- Explanation\n- Notice\n- Request Button"]
      B["Request Form\n- Vehicle Type\n- Purpose\n- Origin/Destination\n- ID\n- Priority\n- Declaration\n- Submit"]
      C["Simulation/Confirmation\n- Success\n- AI Traffic System\n- Animated Route"]
    end
    A -- "Click Request Traffic Priority" --> B
    B -- "Submit Request" --> C
    style Portal fill:#f7f9fa,stroke:#1976d2,stroke-width:2px
    style A fill:#fff,stroke:#d32f2f,stroke-width:2px
    style B fill:#fff,stroke:#1976d2,stroke-width:2px
    style C fill:#fff,stroke:#388e3c,stroke-width:2px
```

### Portal Features (2026 Update)
- Clean, professional, mobile-responsive React UI
- Landing page with government notice and explanation
- Structured emergency request form with validation and dynamic fields
- Animated simulation/confirmation screen
- No backend required for prototype
- All sensitive data protected; only government can access real requests in production
