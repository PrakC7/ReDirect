from collections import Counter
from dataclasses import dataclass


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    bbox_area_ratio: float
    direction: str | None = None


def summarize_detections(detections: list[Detection]) -> dict[str, object]:
    vehicle_labels = {"car", "bus", "truck", "bike", "ambulance", "fire_truck", "police"}
    filtered = [detection for detection in detections if detection.label in vehicle_labels]
    distribution = Counter(detection.label for detection in filtered)
    directional_distribution = Counter(
        detection.direction for detection in filtered if detection.direction
    )
    occupancy_index = round(
        min(sum(detection.bbox_area_ratio for detection in filtered), 1.0), 2
    )

    return {
        "vehicle_count": len(filtered),
        "vehicle_type_distribution": dict(distribution),
        "directional_vehicle_count": dict(directional_distribution),
        "emergency_detected": any(
            detection.label in {"ambulance", "fire_truck", "police"}
            for detection in filtered
        ),
        "occupancy_index": occupancy_index,
    }
