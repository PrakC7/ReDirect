from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    bbox_area_ratio: float
    direction: str | None = None
    speed_kph: float | None = None


def _filter_vehicle_detections(detections: list[Detection]) -> list[Detection]:
    vehicle_labels = {
        "car",
        "bus",
        "truck",
        "bike",
        "ambulance",
        "fire_truck",
        "police",
    }
    return [detection for detection in detections if detection.label in vehicle_labels]


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

    estimated_vehicle_count = vehicle_count_code * count_unit_size
    reported_vehicle_count = estimated_vehicle_count + separate_vehicle_count
    speed_average_divisor = (
        max(estimated_vehicle_count - 2, 1)
        if estimated_vehicle_count and separate_vehicle_count == 0
        else max(reported_vehicle_count, 1)
    )

    return {
        "vehicle_count_code": vehicle_count_code,
        "separate_vehicle_count": separate_vehicle_count,
        "estimated_vehicle_count": estimated_vehicle_count,
        "reported_vehicle_count": reported_vehicle_count,
        "speed_average_divisor": speed_average_divisor,
    }


def build_directional_count_codes(
    detections: list[Detection],
    count_unit_size: int = 10,
) -> list[dict[str, object]]:
    if count_unit_size <= 0:
        raise ValueError("count_unit_size must be greater than zero")

    filtered = _filter_vehicle_detections(detections)
    directional_counts = Counter(
        detection.direction for detection in filtered if detection.direction
    )
    directional_speeds: dict[str, list[float]] = defaultdict(list)

    for detection in filtered:
        if detection.direction and detection.speed_kph is not None:
            directional_speeds[detection.direction].append(detection.speed_kph)

    count_codes: list[dict[str, object]] = []
    for direction, actual_vehicle_count in sorted(directional_counts.items()):
        speed_samples = directional_speeds[direction]
        encoding = _encode_directional_vehicle_count(
            actual_vehicle_count,
            count_unit_size,
        )
        average_speed_kph = (
            round(sum(speed_samples) / encoding["speed_average_divisor"], 1)
            if speed_samples
            else None
        )
        count_codes.append(
            {
                "direction": direction,
                "count_unit_size": count_unit_size,
                "actual_vehicle_count": actual_vehicle_count,
                "average_speed_kph": average_speed_kph,
                **encoding,
            }
        )

    return count_codes


def summarize_detections(detections: list[Detection]) -> dict[str, object]:
    filtered = _filter_vehicle_detections(detections)
    distribution = Counter(detection.label for detection in filtered)
    directional_distribution = Counter(
        detection.direction for detection in filtered if detection.direction
    )
    directional_count_codes = build_directional_count_codes(filtered)
    average_speed_by_direction = {
        count_code["direction"]: count_code["average_speed_kph"]
        for count_code in directional_count_codes
        if count_code["average_speed_kph"] is not None
    }
    occupancy_index = round(
        min(sum(detection.bbox_area_ratio for detection in filtered), 1.0), 2
    )

    return {
        "vehicle_count": len(filtered),
        "vehicle_type_distribution": dict(distribution),
        "directional_vehicle_count": dict(directional_distribution),
        "average_speed_by_direction": average_speed_by_direction,
        "directional_count_codes": directional_count_codes,
        "emergency_detected": any(
            detection.label in {"ambulance", "fire_truck", "police"}
            for detection in filtered
        ),
        "occupancy_index": occupancy_index,
    }
