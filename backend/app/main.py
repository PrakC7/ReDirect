from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import threading

app = FastAPI(title="ReDirect Traffic Control")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# In-memory emergency info store (for demo)
_emergencies = []
_lock = threading.Lock()
EMERGENCY_TTL_SECONDS = 180  # 3 minutes

class EmergencyVehicle(BaseModel):
    id: int
    type: str
    location: str
    timestamp: datetime

GOV_API_KEY = "supersecretkey123"  # In production, use env var or vault

@app.post("/api/v1/emergency/alert")
def add_emergency(ev: EmergencyVehicle):
    with _lock:
        _emergencies.append(ev)
    return {"status": "received"}

@app.get("/api/v1/gov/emergency/active", response_model=List[EmergencyVehicle])
def gov_get_active_emergencies(x_api_key: str = Header(...)):
    if x_api_key != GOV_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    now = datetime.utcnow()
    with _lock:
        active = [e for e in _emergencies if (now - e.timestamp).total_seconds() < EMERGENCY_TTL_SECONDS]
    return active
