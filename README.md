# ReDirect

ReDirect is an AI-assisted traffic optimisation prototype for city control rooms. It is designed to reduce day-to-day congestion across important intersections and also support faster emergency movement for ambulances, police, and fire services.

The current version keeps the same project concept, but improves how decisions are made:

- nearby intersections are checked first within a `20 km` radius
- vehicle motion direction is used to decide whether traffic is actually moving toward a target area
- normal signal timing uses the same logic as emergency routing
- emergency corridors are generated only after controller approval on top of the live network optimisation
- optional wrong-way rule enforcement can be enabled only at specific locations that already have high-quality cameras

## What Is New In This Version

- Direction-aware traffic optimisation for the regular dashboard signal plan
- Incoming pressure scoring based on nearby intersections and inbound vehicle flow
- Radius-first prioritisation so close intersections are handled before the remaining network
- Direction-aware emergency corridor sequencing
- GPS or map-verified emergency requests instead of plain text-only route submission
- Route suggestions that can pick a clearer alternate emergency path when the shortest path is already congested
- Controller approval step before signal override is activated for emergency vehicles
- Edge telemetry ingestion so the dashboard can consume compact area-server numeric packets
- Optional wrong-way violation detection with saved vehicle records for selected high-quality camera sites
- Updated dashboard preview showing inbound pressure and flow direction context
- Cleaner repository structure and preview-ready FastAPI + React demo

## Why This Matters

Most traffic systems only react to queue length at one junction. ReDirect now looks one step wider:

1. It checks nearby intersections.
2. It estimates whether vehicles are actually feeding into a target junction.
3. It prioritises intersections where traffic is both close and moving toward that area.
4. It then adjusts signal recommendations for normal traffic and emergency requests.

This makes the prototype closer to a practical control-room workflow instead of a corridor-only demo.

## System Workflow

### General Traffic Optimisation

1. The backend simulates live vehicle counts for each intersection.
2. Density scoring is calculated from lane count, road width, and congestion history.
3. Nearby intersections inside the `20 km` radius are checked.
4. Local camera-storage servers separate recording input references from counting logic and keep only temporary numeric summaries inside the model.
5. Vehicle motion direction is used to estimate inbound traffic pressure.
6. Signal priority and green timings are updated using both density and directional flow.
7. At selected high-quality camera sites, optional wrong-way detection can save violating vehicle records for enforcement review.

### Emergency Movement Workflow

1. An operator submits an emergency request.
2. The request must include GPS or map-picked coordinates for the origin and destination.
3. The backend resolves the nearest prototype intersections and suggests the clearest route under current live traffic pressure.
4. Traffic police or control-room staff approve the marked emergency vehicle after camera confirmation.
5. Only then is the staged signal corridor activated for the approved route.

## Visual Overview

### System Flow

![System Workflow](docs/system_flow.png)

### System Architecture

![System Architecture](docs/architecture.png)

### Dashboard Preview

![Dashboard](docs/main_dashboard.png)
![Dashboard](docs/dashboard.png)
![Dashboard](docs/dashboard_bottom.png)

The dashboard now highlights:

- live signal-priority cards
- incoming traffic pressure per intersection
- dominant inbound direction from nearby intersections
- optional wrong-way alerts from selected high-quality camera locations
- emergency request submission and confirmation flow
- corridor sequence reasoning with radius-first and movement-alignment details

## Core Features

### Network-Wide Traffic Optimisation

ReDirect continuously ranks intersections using:

- density score
- road importance
- public transport weight
- nearby inbound traffic pressure
- vehicle movement direction
- live telemetry from small local camera servers when it is available

### Direction-Aware Decision Logic

The system does not treat all nearby vehicles equally. It checks whether detected traffic is:

- moving toward the target area
- mostly cross traffic
- moving away from the target area

That makes prioritisation more realistic for both daily traffic balancing and emergency routing.

### Emergency Corridor Planning

Emergency requests still remain a core part of the project. The difference is that corridor generation now reuses the same live optimisation model used by the dashboard.

Emergency routing is now also approval-aware:

- the requester must provide verified coordinates
- the system suggests a primary and fallback route
- the corridor only turns active after controller approval and camera confirmation of the marked emergency vehicle
- controlled red or yellow crossing guidance is shown only for the approved emergency corridor

### Optional Wrong-Way Rule Enforcement

ReDirect can also support traffic-rule enforcement as an optional layer. At selected intersections where high-quality cameras are already installed, the system can:

- detect vehicles moving in the wrong direction
- save compact vehicle information for review
- surface wrong-way alerts in the control-room dashboard
- support enforcement without changing the low-cost baseline design used across the wider network

This is intentionally optional. The core project still works with lightweight traffic metadata and does not depend on expensive camera hardware everywhere.

### Edge-Friendly Design

The project is built around lightweight vehicle metadata rather than heavy full-video processing, making it easier to imagine edge-device deployment.

## Real-World Challenges ReDirect Solves

### Low-Connectivity Traffic Corridors

Many city roads and junctions operate with limited or inconsistent connectivity. ReDirect addresses this smoothly by reusing the small local servers that already store camera feeds for specific area clusters. These preinstalled local servers can also handle ReDirect's five-minute aggregation role, so the project does not need separate new hardware at every location. These small servers can:

- accept camera recording references from the local storage system without moving or deleting the original recordings
- run counting locally as a separate step from input registration
- estimate directional counts
- combine those counts into compact count codes before upload
- detect emergency presence from local inference
- send only compact numeric values to the backend
- keep the control room updated even before a high-bandwidth video stream is available
- keep five-minute combined area snapshots instead of pushing every camera frame to the main optimiser
- clear only the temporary model-generated summaries after a successful send to the main server

Instead of depending on heavy data transfer, it can send packets such as:

- total vehicle count
- occupancy index
- directional vehicle counts
- wrong-way count where optional enforcement is available
- emergency flag
- average speed estimate

This keeps ReDirect fast and practical in low-internet areas because only lightweight numeric telemetry is transmitted from the small area servers to the main optimiser.

ReDirect can also preprocess grouped traffic summaries in a very compact form. For example:

- count code `1` can represent about `10` northbound vehicles with an average speed near `40 km/h`
- count code `2` can represent about `20` southbound vehicles with an average speed near `30 km/h`

To keep the packet both compact and more stable:

- each direction can keep up to `7` extra vehicles separately on top of the `10s` count code
- when the extra count reaches `8`, it rolls into the next count code and the separate remainder resets
- vehicle speed is averaged locally from the actual detections before upload, so speed is not distorted by the compressed count bucket

That means a direction with `17` vehicles can be sent as:

- count code `1`
- separate vehicles `7`

If one more vehicle is added in the same direction, it becomes:

- count code `2`
- separate vehicles `0`

For practical control-room use, full-bucket values are decoded conservatively at the server. So a bucket like `20` is treated as roughly `19` vehicles unless there is a separate remainder attached. This avoids over-prioritising a junction just because the packet was compressed.

This helps the system react quickly while still preserving more usable flow information than a plain rounded count, which is important on mixed Indian traffic corridors where signals need stable but realistic pressure estimates.

This preprocessing can run:

- on the small local server serving a group of nearby cameras
- or directly inside the detection pipeline before the optimisation step

At the camera-cluster level, the small server can keep decimal traffic values locally. For example:

- if current direction shows that a vehicle stream can only feed one nearby target area inside the `20 km` priority radius, the local value is upgraded before forwarding
- if two downstream paths are possible, the local server can split the stream probabilistically such as `0.5 / 0.5`
- these local probability values remain decimal inside the small server store
- when the main traffic optimiser is updated, the transmitted values are rounded using the ceiling value so the central server still works with integer counts

That means the main server receives already-combined directional flow summaries every few minutes, while the camera-level logic still keeps richer decimal estimates inside the local area server.

The practical local flow is now split into three clear layers:

1. `Camera input layer`: the local server receives only recording references and timestamps from the preinstalled camera-storage system.
2. `Counting layer`: ReDirect converts those inputs into directional vehicle counts, speed estimates, emergency flags, and route-probability summaries.
3. `Upload layer`: only the required numeric packet is sent to the main optimiser, and the temporary processed summaries are flushed right after a successful send.

This keeps the prototype efficient and privacy-aware because the traffic optimiser never needs the full recording files for its routine signal decisions.

### Smart Use Of Existing Infrastructure

ReDirect also fits well into mixed city infrastructure:

- most intersections can reuse their local camera-storage servers for numeric summaries and area-level aggregation
- selected intersections with high-quality cameras can additionally support optional wrong-way enforcement and saved vehicle records

This helps the project stay efficient and affordable while still allowing stronger enforcement at important locations where better hardware is already installed. Because the local camera-storage servers are already preinstalled for area monitoring, the same machines can be reused for ReDirect preprocessing without creating a major additional infrastructure cost.

## Optimisation Logic

### Inputs Used

- live vehicle count
- lane count
- road width
- historical congestion
- road priority weight
- movement profile by direction
- optional high-quality camera evidence at selected locations
- low-bandwidth numeric telemetry from small local camera servers

### Decision Layers

1. `density.py` computes congestion pressure.
2. `ai/detection.py` can preprocess raw detections into directional count codes and average-speed summaries.
3. `route_network.py` resolves road-linked prototype paths, nearby anchors, and emergency route options.
4. `network_flow.py` estimates inbound pressure from nearby intersections.
5. `optimization.py` combines density and directional pressure into signal priority.
6. `edge_processor.py` handles low-bandwidth count compression, five-minute area aggregation, and ceiling-rounded uploads.
7. `local_area_server.py` separates camera input references from counting results, keeps only temporary numeric summaries inside the model, and clears them after a successful send.
8. `intersection_priority.py` applies radius-first and motion-aware ordering for corridor logic.
9. `rule_enforcement.py` optionally flags wrong-way violations where high-quality cameras already exist.
10. `emergency.py` keeps requests pending until controller approval activates the corridor.

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
|   |   |   |-- intersection_priority.py
|   |   |   |-- network_flow.py
|   |   |   |-- rule_enforcement.py
|   |   |   `-- optimization.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- .env.example
|   |-- requirements.txt
|   `-- run.py
|-- docs
|-- edge
|   |-- __init__.py
|   |-- edge_processor.py
|   `-- local_area_server.py
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

## Running The Project Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

### Frontend Dev Server

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

### Built-In Preview

The backend can also serve the built frontend preview directly:

```text
http://127.0.0.1:8000/preview
```

### API Docs

```text
http://127.0.0.1:8000/docs
```

## Core API Endpoints

- `GET /health`
- `GET /preview`
- `GET /api/v1/dashboard`
- `POST /api/v1/telemetry/summary`
- `POST /api/v1/telemetry/count-codes`
- `POST /api/v1/emergency/requests`
- `POST /api/v1/emergency/requests/{request_id}/approve`
- `GET /api/v1/emergency/requests`
- `GET /api/v1/gov/emergency/active`
- `GET /api/v1/gov/violations/wrong-way`
- `POST /api/v1/emergency/alert`

## Current Prototype Notes

- The backend uses a lightweight prototype state file so telemetry and active requests survive restarts in demo mode.
- Live traffic values still fall back to simulation when no telemetry packet has been ingested.
- Directional movement is represented using structured motion profiles in the sample network.
- Emergency submission is blocked unless origin and destination are verified from GPS or a map-picked location.
- Emergency corridors remain pending until a controller approves the route after camera confirmation of the marked vehicle.
- Wrong-way violation records are shown as an optional add-on only for selected intersections with existing high-quality cameras.
- The edge module includes low-bandwidth packet examples for preinstalled small local camera-storage servers that send numeric traffic summaries and grouped directional count codes instead of full video streams.
- The local area server flow now separates camera input registration from counting and upload, then clears only temporary model-generated summaries after each successful send.
- Original camera recordings remain in the existing local storage system and are not deleted by the ReDirect model layer.
- The AI and edge folders show how metadata can feed the traffic control layer without requiring a heavy production deployment.

## Documentation

- [Selection brief](docs/selection_brief.md)
- [Government evaluation notes](docs/government_evaluation.md)
- [Project proposal](docs/samadhan_saathi_proposal.md)
