from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Intersection:
    id: int
    name: str
    zone: str
    latitude: float
    longitude: float
    lane_count: int
    road_width_m: float
    road_priority_weight: float
    historical_congestion: float
    live_vehicle_count: int
    signal_group: str


@dataclass(slots=True)
class EmergencyRoute:
    request_id: str
    severity_level: int
    source: str
    route_intersections: list[int]
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
