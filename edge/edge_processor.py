from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class EdgeReading:
    intersection_id: int
    vehicle_count: int
    occupancy_index: float
    emergency_detected: bool
    captured_at: datetime
    directional_vehicle_count: dict[str, int] | None = None
    wrong_way_count: int = 0
    average_speed_kph: float | None = None


@dataclass(slots=True)
class LowBandwidthTelemetry:
    intersection_id: int
    sequence_id: int
    total_vehicle_count: int
    occupancy_index_x100: int
    emergency_flag: int
    wrong_way_count: int
    northbound_count: int
    southbound_count: int
    eastbound_count: int
    westbound_count: int
    average_speed_kph_x10: int
    captured_epoch: int


def compress_reading(reading: EdgeReading) -> dict[str, object]:
    payload = asdict(reading)
    payload["captured_at"] = reading.captured_at.isoformat()
    payload["occupancy_index"] = round(reading.occupancy_index, 2)
    if reading.average_speed_kph is not None:
        payload["average_speed_kph"] = round(reading.average_speed_kph, 1)
    return payload


def build_low_bandwidth_packet(
    reading: EdgeReading,
    sequence_id: int,
) -> dict[str, int]:
    direction_counts = reading.directional_vehicle_count or {}
    packet = LowBandwidthTelemetry(
        intersection_id=reading.intersection_id,
        sequence_id=sequence_id,
        total_vehicle_count=reading.vehicle_count,
        occupancy_index_x100=int(round(reading.occupancy_index * 100)),
        emergency_flag=int(reading.emergency_detected),
        wrong_way_count=reading.wrong_way_count,
        northbound_count=direction_counts.get("northbound", 0),
        southbound_count=direction_counts.get("southbound", 0),
        eastbound_count=direction_counts.get("eastbound", 0),
        westbound_count=direction_counts.get("westbound", 0),
        average_speed_kph_x10=int(round((reading.average_speed_kph or 0.0) * 10)),
        captured_epoch=int(reading.captured_at.timestamp()),
    )
    return asdict(packet)
