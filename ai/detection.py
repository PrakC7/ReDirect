from collections import Counter, defaultdict
from dataclasses import dataclass
from math import ceil


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
        vehicle_count_code = ceil(actual_vehicle_count / count_unit_size)
        speed_samples = directional_speeds[direction]
        average_speed_kph = (
            round(sum(speed_samples) / len(speed_samples), 1)
            if speed_samples
            else None
        )
        count_codes.append(
            {
                "direction": direction,
                "vehicle_count_code": vehicle_count_code,
                "count_unit_size": count_unit_size,
                "estimated_vehicle_count": vehicle_count_code * count_unit_size,
                "actual_vehicle_count": actual_vehicle_count,
                "average_speed_kph": average_speed_kph,
            }
        )

    return count_codes


def summarize_detections(detections: list[Detection]) -> dict[str, object]:
    filtered = _filter_vehicle_detections(detections)
    distribution = Counter(detection.label for detection in filtered)
    directional_distribution = Counter(
        detection.direction for detection in filtered if detection.direction
    )
    directional_speed_samples: dict[str, list[float]] = defaultdict(list)
    for detection in filtered:
        if detection.direction and detection.speed_kph is not None:
            directional_speed_samples[detection.direction].append(detection.speed_kph)

    average_speed_by_direction = {
        direction: round(sum(speed_samples) / len(speed_samples), 1)
        for direction, speed_samples in sorted(directional_speed_samples.items())
        if speed_samples
    }
    occupancy_index = round(
        min(sum(detection.bbox_area_ratio for detection in filtered), 1.0), 2
    )

    return {
        "vehicle_count": len(filtered),
        "vehicle_type_distribution": dict(distribution),
        "directional_vehicle_count": dict(directional_distribution),
        "average_speed_by_direction": average_speed_by_direction,
        "directional_count_codes": build_directional_count_codes(filtered),
        "emergency_detected": any(
            detection.label in {"ambulance", "fire_truck", "police"}
            for detection in filtered
        ),
        "occupancy_index": occupancy_index,
    }
