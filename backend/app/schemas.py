from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PriorityLevel = Literal["Critical", "High", "Medium"]
MovementAlignment = Literal[
    "at-zone",
    "towards-zone",
    "cross-traffic",
    "away-from-zone",
    "undetermined",
]


class IntersectionSnapshot(BaseModel):
    id: int
    name: str
    zone: str
    signal_group: str
    live_vehicle_count: int
    density_score: float
    priority_score: float
    incoming_pressure_score: float
    primary_inbound_direction: str | None = None
    nearby_inbound_vehicle_share: float
    recommended_green_seconds: int
    status: str


class IntersectionPriorityStep(BaseModel):
    intersection_id: int
    intersection_name: str
    distance_km: float | None
    priority_phase: Literal["radius-first", "remaining"]
    target_flow_direction: str | None = None
    dominant_flow_direction: str | None = None
    approaching_zone: bool
    approaching_vehicle_share: float = Field(..., ge=0.0, le=1.0)
    movement_alignment: MovementAlignment


class CorridorStep(BaseModel):
    intersection_id: int
    intersection_name: str
    green_from: datetime
    green_to: datetime
    distance_km: float | None = None
    priority_phase: Literal["radius-first", "remaining"] | None = None
    target_flow_direction: str | None = None
    approaching_zone: bool | None = None
    approaching_vehicle_share: float | None = Field(default=None, ge=0.0, le=1.0)
    movement_alignment: MovementAlignment | None = None


class EmergencyRequestCreate(BaseModel):
    requester_name: str = Field(..., min_length=2, max_length=60)
    department: str = Field(..., min_length=2, max_length=80)
    vehicle_type: str = Field(..., min_length=2, max_length=40)
    purpose: str = Field(..., min_length=2, max_length=80)
    origin: str = Field(..., min_length=2, max_length=120)
    destination: str = Field(..., min_length=2, max_length=120)
    return_destination: str | None = Field(default=None, max_length=120)
    vehicle_id_type: str = Field(..., min_length=2, max_length=40)
    vehicle_id: str = Field(..., min_length=2, max_length=40)
    priority: PriorityLevel
    estimated_travel_minutes: int = Field(..., ge=1, le=180)
    route_notes: str | None = Field(default=None, max_length=240)


class ActiveEmergencySummary(BaseModel):
    request_id: str
    vehicle_type: str
    priority: PriorityLevel
    origin: str
    destination: str
    submitted_at: datetime
    suggested_time_saved_minutes: int


class EmergencyRequestRecord(EmergencyRequestCreate):
    request_id: str
    status: str
    submitted_at: datetime
    suggested_time_saved_minutes: int
    corridor_window_seconds: int
    priority_radius_km: int
    corridor: list[CorridorStep]
    priority_intersections: list[IntersectionPriorityStep]


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    next_refresh_seconds: int
    active_emergency_count: int
    average_clearance_gain_minutes: int
    priority_radius_km: int
    intersections: list[IntersectionSnapshot]
    active_requests: list[ActiveEmergencySummary]


class LegacyEmergencyAlert(BaseModel):
    id: int
    type: str
    location: str
    timestamp: datetime
