from dataclasses import asdict, dataclass
from datetime import datetime
from math import ceil


@dataclass(slots=True)
class EdgeReading:
    intersection_id: int
    vehicle_count: int
    occupancy_index: float
    emergency_detected: bool
    captured_at: datetime
    directional_vehicle_count: dict[str, int] | None = None
    wrong_way_count: int = 0
    average_speed_by_direction: dict[str, float] | None = None
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


@dataclass(slots=True)
class DirectionalCountCode:
    direction: str
    vehicle_count_code: int
    average_speed_kph_x10: int


@dataclass(slots=True)
class DirectionalCountCodePacket:
    intersection_id: int
    sequence_id: int
    count_unit_size: int
    emergency_flag: int
    wrong_way_count: int
    captured_epoch: int
    flows: list[DirectionalCountCode]


def compress_reading(reading: EdgeReading) -> dict[str, object]:
    payload = asdict(reading)
    payload["captured_at"] = reading.captured_at.isoformat()
    payload["occupancy_index"] = round(reading.occupancy_index, 2)
    if reading.average_speed_by_direction:
        payload["average_speed_by_direction"] = {
            direction: round(speed_kph, 1)
            for direction, speed_kph in reading.average_speed_by_direction.items()
        }
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


def build_directional_count_code_packet(
    reading: EdgeReading,
    sequence_id: int,
    count_unit_size: int = 10,
) -> dict[str, object]:
    if count_unit_size <= 0:
        raise ValueError("count_unit_size must be greater than zero")

    direction_counts = reading.directional_vehicle_count or {}
    speed_by_direction = reading.average_speed_by_direction or {}
    flow_units = [
        DirectionalCountCode(
            direction=direction,
            vehicle_count_code=ceil(vehicle_count / count_unit_size),
            average_speed_kph_x10=int(
                round(
                    speed_by_direction.get(direction, reading.average_speed_kph or 0.0)
                    * 10
                )
            ),
        )
        for direction, vehicle_count in sorted(direction_counts.items())
        if vehicle_count > 0
    ]
    packet = DirectionalCountCodePacket(
        intersection_id=reading.intersection_id,
        sequence_id=sequence_id,
        count_unit_size=count_unit_size,
        emergency_flag=int(reading.emergency_detected),
        wrong_way_count=reading.wrong_way_count,
        captured_epoch=int(reading.captured_at.timestamp()),
        flows=flow_units,
    )
    return asdict(packet)


def decode_directional_count_code_packet(
    packet: dict[str, object],
) -> dict[str, object]:
    count_unit_size = int(packet["count_unit_size"])
    flow_units = packet.get("flows", [])

    directional_vehicle_count: dict[str, int] = {}
    average_speed_by_direction: dict[str, float] = {}
    weighted_speed_total = 0.0
    weighted_vehicle_total = 0

    for flow in flow_units:
        direction = str(flow["direction"])
        estimated_vehicle_count = int(flow["vehicle_count_code"]) * count_unit_size
        average_speed_kph = round(int(flow["average_speed_kph_x10"]) / 10, 1)
        directional_vehicle_count[direction] = estimated_vehicle_count
        average_speed_by_direction[direction] = average_speed_kph
        weighted_speed_total += estimated_vehicle_count * average_speed_kph
        weighted_vehicle_total += estimated_vehicle_count

    return {
        "intersection_id": int(packet["intersection_id"]),
        "sequence_id": int(packet["sequence_id"]),
        "captured_epoch": int(packet["captured_epoch"]),
        "emergency_detected": bool(packet["emergency_flag"]),
        "wrong_way_count": int(packet["wrong_way_count"]),
        "vehicle_count": sum(directional_vehicle_count.values()),
        "directional_vehicle_count": directional_vehicle_count,
        "average_speed_by_direction": average_speed_by_direction,
        "average_speed_kph": round(
            weighted_speed_total / max(weighted_vehicle_total, 1),
            1,
        ),
    }
