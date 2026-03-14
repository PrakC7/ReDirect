from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PriorityLevel = Literal["Critical", "High", "Medium"]
LocationVerificationSource = Literal["device-gps", "maps-picked"]
ApprovalMethod = Literal["camera-verified"]
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
    optional_enforcement_enabled: bool = False
    expected_flow_direction: str | None = None
    wrong_way_alert_count: int = 0
    wrong_way_vehicle_share: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_green_seconds: int
    data_source: Literal["edge-telemetry", "prototype-simulation"]
    last_telemetry_at: datetime | None = None
    status: str


class WrongWayViolationRecord(BaseModel):
    intersection_id: int
    intersection_name: str
    vehicle_type: str
    vehicle_identifier: str
    observed_direction: str
    allowed_direction: str
    captured_at: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_source: str


class IntersectionPriorityStep(BaseModel):
    intersection_id: int
    intersection_name: str
    distance_km: float | None
    road_distance_km: float | None = None
    priority_phase: Literal["radius-first", "remaining"]
    target_flow_direction: str | None = None
    dominant_flow_direction: str | None = None
    approaching_zone: bool
    approaching_vehicle_share: float = Field(..., ge=0.0, le=1.0)
    on_resolved_route: bool = False
    movement_alignment: MovementAlignment


class CorridorStep(BaseModel):
    intersection_id: int
    intersection_name: str
    green_from: datetime
    green_to: datetime
    distance_km: float | None = None
    road_distance_km: float | None = None
    priority_phase: Literal["radius-first", "remaining"] | None = None
    target_flow_direction: str | None = None
    approaching_zone: bool | None = None
    approaching_vehicle_share: float | None = Field(default=None, ge=0.0, le=1.0)
    on_resolved_route: bool | None = None
    movement_alignment: MovementAlignment | None = None


class EmergencyRequestCreate(BaseModel):
    requester_name: str = Field(..., min_length=2, max_length=60)
    department: str = Field(..., min_length=2, max_length=80)
    vehicle_type: str = Field(..., min_length=2, max_length=40)
    purpose: str = Field(..., min_length=2, max_length=80)
    origin: str = Field(..., min_length=2, max_length=120)
    origin_latitude: float = Field(..., ge=-90.0, le=90.0)
    origin_longitude: float = Field(..., ge=-180.0, le=180.0)
    origin_location_source: LocationVerificationSource
    destination: str = Field(..., min_length=2, max_length=120)
    destination_latitude: float = Field(..., ge=-90.0, le=90.0)
    destination_longitude: float = Field(..., ge=-180.0, le=180.0)
    destination_location_source: LocationVerificationSource
    return_destination: str | None = Field(default=None, max_length=120)
    return_destination_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    return_destination_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    return_destination_location_source: LocationVerificationSource | None = None
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
    status: str


class EmergencyRouteSuggestion(BaseModel):
    route_id: str
    label: str
    reason: str
    total_distance_km: float
    estimated_travel_minutes: int
    congestion_score: float
    intersections: list[str]


class ControllerApprovalRecord(BaseModel):
    approved_at: datetime
    controller_name: str
    controller_role: str
    approval_method: ApprovalMethod
    camera_reference: str
    approved_route_id: str
    signal_override_authorized: bool


class EmergencyApprovalRequest(BaseModel):
    route_id: str = Field(..., min_length=3, max_length=40)
    controller_name: str = Field(..., min_length=2, max_length=60)
    controller_role: str = Field(..., min_length=2, max_length=60)
    approval_method: ApprovalMethod
    camera_reference: str = Field(..., min_length=3, max_length=120)
    signal_override_authorized: bool = True


class EmergencyRequestRecord(EmergencyRequestCreate):
    request_id: str
    status: str
    submitted_at: datetime
    suggested_time_saved_minutes: int
    corridor_window_seconds: int
    priority_radius_km: int
    approval_required: bool
    approved_route_id: str | None = None
    route_suggestions: list[EmergencyRouteSuggestion]
    controller_approval: ControllerApprovalRecord | None = None
    signal_override_guidance: str
    corridor: list[CorridorStep]
    priority_intersections: list[IntersectionPriorityStep]


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    next_refresh_seconds: int
    active_emergency_count: int
    average_clearance_gain_minutes: int
    priority_radius_km: int
    live_telemetry_intersections: int
    enforcement_enabled_intersections: int
    wrong_way_violation_count: int
    optional_enforcement_note: str
    intersections: list[IntersectionSnapshot]
    active_requests: list[ActiveEmergencySummary]
    wrong_way_alerts: list[WrongWayViolationRecord]


class LegacyEmergencyAlert(BaseModel):
    id: int
    type: str
    location: str
    timestamp: datetime


class TelemetrySummaryIn(BaseModel):
    intersection_id: int
    vehicle_count: int = Field(..., ge=0, le=5000)
    occupancy_index: float = Field(..., ge=0.0, le=1.0)
    directional_vehicle_count: dict[str, int] = Field(default_factory=dict)
    vehicle_type_distribution: dict[str, int] = Field(default_factory=dict)
    average_speed_by_direction: dict[str, float] = Field(default_factory=dict)
    average_speed_kph: float | None = Field(default=None, ge=0.0, le=200.0)
    emergency_detected: bool = False
    wrong_way_count: int = Field(default=0, ge=0, le=1000)
    captured_at: datetime | None = None


class DirectionalCountCodeFlowIn(BaseModel):
    direction: str
    vehicle_count_code: int = Field(..., ge=0, le=500)
    separate_vehicle_count: int = Field(default=0, ge=0, le=9)
    average_speed_kph_x10: int = Field(..., ge=0, le=2000)


class DirectionalCountCodePacketIn(BaseModel):
    intersection_id: int
    sequence_id: int = Field(..., ge=0)
    count_unit_size: int = Field(default=10, ge=1, le=50)
    emergency_flag: int = Field(default=0, ge=0, le=1)
    wrong_way_count: int = Field(default=0, ge=0, le=1000)
    captured_epoch: int = Field(..., ge=0)
    flows: list[DirectionalCountCodeFlowIn] = Field(default_factory=list)


class TelemetryIngestResponse(BaseModel):
    intersection_id: int
    data_source: Literal["edge-telemetry"]
    captured_at: datetime
    vehicle_count: int
    status: str
