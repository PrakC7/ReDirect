from collections import defaultdict
from dataclasses import asdict, dataclass, field
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
    separate_vehicle_count: int
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


@dataclass(slots=True)
class CameraTargetOption:
    target_intersection_id: int
    distance_km: float
    reachable_by_direction: bool = True


@dataclass(slots=True)
class CameraFlowReading:
    area_id: str
    camera_id: str
    controlled_intersection_id: int
    captured_at: datetime
    direction: str
    vehicle_count: int
    average_speed_kph: float | None = None
    emergency_detected: bool = False
    wrong_way_count: int = 0
    target_options: list[CameraTargetOption] = field(default_factory=list)


@dataclass(slots=True)
class AreaFlowAllocation:
    camera_id: str
    direction: str
    target_intersection_id: int
    routing_probability: float
    expected_vehicle_count: float
    distance_km: float


@dataclass(slots=True)
class AreaSmallServerSnapshot:
    area_id: str
    controlled_intersection_id: int
    window_minutes: int
    priority_radius_km: float
    generated_at: datetime
    observation_count: int
    decimal_directional_vehicle_count: dict[str, float]
    decimal_target_vehicle_count: dict[int, float]
    average_speed_by_direction: dict[str, float]
    emergency_detected: bool
    wrong_way_count: int
    flows: list[AreaFlowAllocation]


def _encode_directional_vehicle_count(
    actual_vehicle_count: int,
    count_unit_size: int,
) -> dict[str, int]:
    if count_unit_size <= 0:
        raise ValueError("count_unit_size must be greater than zero")

    vehicle_count_code, separate_vehicle_count = divmod(
        actual_vehicle_count,
        count_unit_size,
    )
    rollover_threshold = max(count_unit_size - 2, 1)
    if separate_vehicle_count >= rollover_threshold:
        vehicle_count_code += 1
        separate_vehicle_count = 0

    compressed_vehicle_count_upper_bound = vehicle_count_code * count_unit_size
    if compressed_vehicle_count_upper_bound and separate_vehicle_count == 0:
        decoded_vehicle_count_min = max(
            compressed_vehicle_count_upper_bound - 2,
            1,
        )
        decoded_vehicle_count_estimate = max(
            compressed_vehicle_count_upper_bound - 1,
            1,
        )
    else:
        decoded_vehicle_count_min = (
            compressed_vehicle_count_upper_bound + separate_vehicle_count
        )
        decoded_vehicle_count_estimate = decoded_vehicle_count_min

    decoded_vehicle_count_max = (
        compressed_vehicle_count_upper_bound
        if compressed_vehicle_count_upper_bound and separate_vehicle_count == 0
        else decoded_vehicle_count_estimate
    )

    return {
        "vehicle_count_code": vehicle_count_code,
        "separate_vehicle_count": separate_vehicle_count,
        "compressed_vehicle_count_upper_bound": compressed_vehicle_count_upper_bound,
        "decoded_vehicle_count_min": decoded_vehicle_count_min,
        "decoded_vehicle_count_estimate": decoded_vehicle_count_estimate,
        "decoded_vehicle_count_max": decoded_vehicle_count_max,
    }


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


def _rounded_decimal_map(values: dict[object, float], decimals: int = 2) -> dict[object, float]:
    return {
        key: round(value, decimals)
        for key, value in values.items()
        if value > 0
    }


def _allocation_boost(option_count: int) -> float:
    if option_count <= 1:
        return 1.15
    return 1.0


def allocate_camera_flow(
    reading: CameraFlowReading,
    priority_radius_km: float = 20.0,
) -> list[AreaFlowAllocation]:
    eligible_targets = [
        option
        for option in reading.target_options
        if option.reachable_by_direction and option.distance_km <= priority_radius_km
    ]
    if not eligible_targets:
        return []

    probability = round(1.0 / len(eligible_targets), 2)
    boosted_vehicle_count = reading.vehicle_count * _allocation_boost(
        len(eligible_targets)
    )

    return [
        AreaFlowAllocation(
            camera_id=reading.camera_id,
            direction=reading.direction,
            target_intersection_id=option.target_intersection_id,
            routing_probability=probability,
            expected_vehicle_count=round(boosted_vehicle_count * probability, 2),
            distance_km=option.distance_km,
        )
        for option in eligible_targets
    ]


def build_area_small_server_snapshot(
    readings: list[CameraFlowReading],
    area_id: str,
    controlled_intersection_id: int,
    generated_at: datetime | None = None,
    window_minutes: int = 5,
    priority_radius_km: float = 20.0,
) -> dict[str, object]:
    snapshot_time = generated_at or datetime.utcnow()
    window_start = snapshot_time.timestamp() - (window_minutes * 60)
    relevant_readings = [
        reading
        for reading in readings
        if (
            reading.area_id == area_id
            and reading.controlled_intersection_id == controlled_intersection_id
            and reading.captured_at.timestamp() >= window_start
        )
    ]

    decimal_directional_vehicle_count: dict[str, float] = defaultdict(float)
    decimal_target_vehicle_count: dict[int, float] = defaultdict(float)
    speed_totals: dict[str, float] = defaultdict(float)
    speed_weights: dict[str, float] = defaultdict(float)
    flows: list[AreaFlowAllocation] = []
    emergency_detected = False
    wrong_way_count = 0

    for reading in relevant_readings:
        emergency_detected = emergency_detected or reading.emergency_detected
        wrong_way_count += reading.wrong_way_count
        allocations = allocate_camera_flow(reading, priority_radius_km)
        if not allocations:
            continue

        for allocation in allocations:
            flows.append(allocation)
            decimal_directional_vehicle_count[allocation.direction] += (
                allocation.expected_vehicle_count
            )
            decimal_target_vehicle_count[allocation.target_intersection_id] += (
                allocation.expected_vehicle_count
            )
            if reading.average_speed_kph is not None:
                speed_totals[allocation.direction] += (
                    allocation.expected_vehicle_count * reading.average_speed_kph
                )
                speed_weights[allocation.direction] += allocation.expected_vehicle_count

    average_speed_by_direction = {
        direction: round(speed_totals[direction] / max(speed_weights[direction], 1.0), 1)
        for direction in speed_totals
        if speed_weights[direction] > 0
    }
    snapshot = AreaSmallServerSnapshot(
        area_id=area_id,
        controlled_intersection_id=controlled_intersection_id,
        window_minutes=window_minutes,
        priority_radius_km=priority_radius_km,
        generated_at=snapshot_time,
        observation_count=len(relevant_readings),
        decimal_directional_vehicle_count=_rounded_decimal_map(
            decimal_directional_vehicle_count
        ),
        decimal_target_vehicle_count=_rounded_decimal_map(
            decimal_target_vehicle_count
        ),
        average_speed_by_direction=average_speed_by_direction,
        emergency_detected=emergency_detected,
        wrong_way_count=wrong_way_count,
        flows=flows,
    )
    payload = asdict(snapshot)
    payload["generated_at"] = snapshot.generated_at.isoformat()
    return payload


def build_optimizer_upload_from_area_snapshot(
    snapshot: dict[str, object],
    sequence_id: int,
    occupancy_index: float | None = None,
) -> dict[str, int]:
    decimal_directional_vehicle_count = {
        str(direction): float(count)
        for direction, count in snapshot.get("decimal_directional_vehicle_count", {}).items()
    }
    average_speed_by_direction = {
        str(direction): round(float(speed_kph), 1)
        for direction, speed_kph in snapshot.get("average_speed_by_direction", {}).items()
    }
    directional_vehicle_count = {
        direction: int(ceil(count))
        for direction, count in decimal_directional_vehicle_count.items()
    }
    vehicle_count = sum(directional_vehicle_count.values())
    average_speed_total = sum(
        directional_vehicle_count.get(direction, 0)
        * average_speed_by_direction.get(direction, 0.0)
        for direction in directional_vehicle_count
    )
    average_speed_kph = round(
        average_speed_total / max(vehicle_count, 1),
        1,
    )
    reading = EdgeReading(
        intersection_id=int(snapshot["controlled_intersection_id"]),
        vehicle_count=vehicle_count,
        occupancy_index=round(
            occupancy_index
            if occupancy_index is not None
            else min(vehicle_count / 120.0, 1.0),
            2,
        ),
        emergency_detected=bool(snapshot.get("emergency_detected", False)),
        captured_at=datetime.fromisoformat(str(snapshot["generated_at"])),
        directional_vehicle_count=directional_vehicle_count,
        wrong_way_count=int(snapshot.get("wrong_way_count", 0)),
        average_speed_by_direction=average_speed_by_direction,
        average_speed_kph=average_speed_kph,
    )
    return build_low_bandwidth_packet(reading, sequence_id)


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
    flow_units = []
    for direction, vehicle_count in sorted(direction_counts.items()):
        if vehicle_count <= 0:
            continue

        encoding = _encode_directional_vehicle_count(vehicle_count, count_unit_size)
        flow_units.append(
            DirectionalCountCode(
                direction=direction,
                vehicle_count_code=encoding["vehicle_count_code"],
                separate_vehicle_count=encoding["separate_vehicle_count"],
                average_speed_kph_x10=int(
                    round(
                        speed_by_direction.get(
                            direction,
                            reading.average_speed_kph or 0.0,
                        )
                        * 10
                    )
                ),
            )
        )
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
    directional_vehicle_count_range: dict[str, dict[str, int]] = {}
    average_speed_by_direction: dict[str, float] = {}
    weighted_speed_total = 0.0
    weighted_vehicle_total = 0

    for flow in flow_units:
        direction = str(flow["direction"])
        encoding = _encode_directional_vehicle_count(
            int(flow["vehicle_count_code"]) * count_unit_size
            + int(flow.get("separate_vehicle_count", 0)),
            count_unit_size,
        )
        average_speed_kph = round(int(flow["average_speed_kph_x10"]) / 10, 1)
        directional_vehicle_count[direction] = encoding["decoded_vehicle_count_estimate"]
        directional_vehicle_count_range[direction] = {
            "min": encoding["decoded_vehicle_count_min"],
            "max": encoding["decoded_vehicle_count_max"],
        }
        average_speed_by_direction[direction] = average_speed_kph
        weighted_speed_total += (
            encoding["decoded_vehicle_count_estimate"] * average_speed_kph
        )
        weighted_vehicle_total += encoding["decoded_vehicle_count_estimate"]

    return {
        "intersection_id": int(packet["intersection_id"]),
        "sequence_id": int(packet["sequence_id"]),
        "captured_epoch": int(packet["captured_epoch"]),
        "emergency_detected": bool(packet["emergency_flag"]),
        "wrong_way_count": int(packet["wrong_way_count"]),
        "vehicle_count": sum(directional_vehicle_count.values()),
        "directional_vehicle_count": directional_vehicle_count,
        "directional_vehicle_count_range": directional_vehicle_count_range,
        "average_speed_by_direction": average_speed_by_direction,
        "average_speed_kph": round(
            weighted_speed_total / max(weighted_vehicle_total, 1),
            1,
        ),
    }
