# ReDirect Selection Brief

## One-Line Pitch

ReDirect is a smart traffic optimisation platform for Indian cities that improves normal traffic flow, enables faster emergency corridors, and optionally supports wrong-way enforcement at selected locations.

## Why It Stands Out

- solves a real and frequent public problem, not a niche scenario
- fits Indian mixed-traffic conditions better than lane-dependent models
- combines traffic optimisation and emergency response in one system
- supports low-connectivity deployment using numeric edge telemetry
- stays affordable by using selective premium features instead of requiring high-end hardware everywhere

## What Reviewers Can Quickly Understand

### Problem

Cities need faster traffic decisions, better emergency movement, and more practical smart-traffic deployment models.

### Solution

ReDirect uses live traffic density, nearby-intersection pressure, vehicle direction reasoning, and two-minute local-server summaries to produce smarter signal decisions.

### What The Local-Server Model Solves

- removes the need to push full camera footage to the central server
- keeps optimisation usable even in low-connectivity areas
- reduces delay by combining area traffic information locally before upload
- keeps wrong-way violations with the local control room where local action is faster and more relevant

### How It Works In Brief

Existing local camera-storage servers keep the recordings, ReDirect counts vehicles from those local inputs, combines the traffic summary every two minutes, and forwards only compact signal-optimisation data to the main server.

### Innovation

- direction-aware optimisation
- radius-first nearby intersection prioritisation
- emergency routing built on the same live traffic logic
- optional wrong-way alerting at selected premium-camera locations, handled locally where useful

### Feasibility

- modular FastAPI + React prototype
- low-bandwidth roadside telemetry concept
- phased rollout path
- compatible with existing infrastructure

### Public Impact

- reduced congestion
- better corridor-level traffic movement
- faster emergency response support
- improved operational visibility for traffic control rooms

## Recommended Reviewer Takeaway

ReDirect is a strong selection candidate because it is practical, scalable, and clearly useful. It shows a realistic path from prototype to city deployment while addressing both everyday traffic problems and high-value emergency scenarios.
