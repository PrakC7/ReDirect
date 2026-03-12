from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class EdgeReading:
    intersection_id: int
    vehicle_count: int
    occupancy_index: float
    emergency_detected: bool
    captured_at: datetime


def compress_reading(reading: EdgeReading) -> dict[str, object]:
    payload = asdict(reading)
    payload["captured_at"] = reading.captured_at.isoformat()
    payload["occupancy_index"] = round(reading.occupancy_index, 2)
    return payload
