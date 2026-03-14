from datetime import datetime, timedelta

from app.db.models import Intersection
from app.schemas import WrongWayViolationRecord

OPPOSITE_DIRECTION = {
    "northbound": "southbound",
    "southbound": "northbound",
    "eastbound": "westbound",
    "westbound": "eastbound",
}
EVIDENCE_VEHICLE_TYPES = [
    "Car",
    "Bike",
    "Scooter",
    "Van",
    "Truck",
]


def _masked_vehicle_identifier(
    intersection_id: int,
    index: int,
) -> str:
    suffix = f"{((intersection_id * 37) + (index * 53)) % 10000:04d}"
    return f"DL-01-XX-{suffix}"


def _build_violation_record(
    intersection: Intersection,
    observed_direction: str,
    allowed_direction: str,
    confidence: float,
    captured_at: datetime,
    index: int,
) -> WrongWayViolationRecord:
    vehicle_type = EVIDENCE_VEHICLE_TYPES[
        (intersection.id + index) % len(EVIDENCE_VEHICLE_TYPES)
    ]
    return WrongWayViolationRecord(
        intersection_id=intersection.id,
        intersection_name=intersection.name,
        vehicle_type=vehicle_type,
        vehicle_identifier=_masked_vehicle_identifier(intersection.id, index),
        observed_direction=observed_direction,
        allowed_direction=allowed_direction,
        captured_at=captured_at - timedelta(minutes=index * 2),
        confidence=round(confidence, 2),
        evidence_source=(
            intersection.enforcement_camera_quality
            or "Existing high-quality roadside camera"
        ),
    )


def build_wrong_way_enforcement(
    intersections: list[Intersection],
    captured_at: datetime | None = None,
) -> tuple[dict[int, dict[str, object]], list[WrongWayViolationRecord], int]:
    observed_at = captured_at or datetime.utcnow()
    by_intersection_id: dict[int, dict[str, object]] = {}
    violations: list[WrongWayViolationRecord] = []
    enabled_intersections = 0

    for intersection in intersections:
        if (
            not intersection.enforcement_camera_enabled
            or not intersection.expected_flow_direction
        ):
            by_intersection_id[intersection.id] = {
                "optional_enforcement_enabled": False,
                "expected_flow_direction": None,
                "wrong_way_alert_count": 0,
                "wrong_way_vehicle_share": 0.0,
            }
            continue

        enabled_intersections += 1
        allowed_direction = intersection.expected_flow_direction
        observed_direction = OPPOSITE_DIRECTION.get(allowed_direction)
        total_flow = sum(intersection.movement_profile.values()) or 1
        allowed_flow_count = intersection.movement_profile.get(allowed_direction, 0)
        wrong_way_count = (
            intersection.movement_profile.get(observed_direction, 0)
            if observed_direction
            else 0
        )
        monitored_axis_total = max(allowed_flow_count + wrong_way_count, 1)
        wrong_way_share = round(wrong_way_count / monitored_axis_total, 2)
        cross_traffic_count = max(total_flow - monitored_axis_total, 0)

        record_count = 0
        if (
            wrong_way_count >= 8
            or (wrong_way_count >= 5 and wrong_way_share >= 0.25)
        ):
            record_count = 2
        elif (
            wrong_way_count >= 3
            and wrong_way_share >= 0.12
            and wrong_way_count > max(cross_traffic_count // 3, 0)
        ):
            record_count = 1

        confidence = min(0.97, 0.68 + (wrong_way_share * 1.1))
        intersection_records = []
        for index in range(record_count):
            if observed_direction is None:
                break
            intersection_records.append(
                _build_violation_record(
                    intersection,
                    observed_direction,
                    allowed_direction,
                    confidence,
                    observed_at,
                    index,
                )
            )

        violations.extend(intersection_records)
        by_intersection_id[intersection.id] = {
            "optional_enforcement_enabled": True,
            "expected_flow_direction": allowed_direction,
            "wrong_way_alert_count": len(intersection_records),
            "wrong_way_vehicle_share": wrong_way_share,
        }

    violations.sort(
        key=lambda record: (record.confidence, record.captured_at),
        reverse=True,
    )
    return by_intersection_id, violations, enabled_intersections
