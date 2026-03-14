from math import asin, cos, radians, sin, sqrt

from app.db.models import Intersection
from app.schemas import IntersectionPriorityStep

PRIORITY_RADIUS_KM = 20.0


def distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    earth_radius_km = 6371.0
    lat_delta = radians(second_latitude - first_latitude)
    lon_delta = radians(second_longitude - first_longitude)
    first_lat = radians(first_latitude)
    second_lat = radians(second_latitude)

    haversine = (
        sin(lat_delta / 2) ** 2
        + cos(first_lat) * cos(second_lat) * sin(lon_delta / 2) ** 2
    )
    return earth_radius_km * 2 * asin(sqrt(haversine))


def resolve_anchor_intersection(
    request_text: str,
    intersections: list[Intersection],
) -> Intersection | None:
    normalized = request_text.lower()
    best_match: tuple[int, Intersection] | None = None

    for intersection in intersections:
        searchable_parts = [
            intersection.name.lower(),
            intersection.zone.lower(),
            intersection.signal_group.lower(),
        ]
        score = 0

        for part in searchable_parts:
            if part in normalized:
                score += 4

        for token in normalized.replace(",", " ").split():
            if any(token in part for part in searchable_parts):
                score += 1

        if score > 0 and (best_match is None or score > best_match[0]):
            best_match = (score, intersection)

    return best_match[1] if best_match else None


def build_intersection_priority_plan(
    anchor: Intersection | None,
    intersections: list[Intersection],
    priority_scores: dict[int, float],
    radius_km: float = PRIORITY_RADIUS_KM,
) -> tuple[list[Intersection], list[IntersectionPriorityStep]]:
    ranked: list[tuple[Intersection, float | None, bool, float]] = []

    for intersection in intersections:
        anchor_distance = None
        within_radius = False
        if anchor is not None:
            anchor_distance = round(
                distance_km(
                    anchor.latitude,
                    anchor.longitude,
                    intersection.latitude,
                    intersection.longitude,
                ),
                1,
            )
            within_radius = anchor_distance <= radius_km

        ranked.append(
            (
                intersection,
                anchor_distance,
                within_radius,
                priority_scores.get(intersection.id, 0.0),
            )
        )

    ordered = sorted(
        ranked,
        key=lambda item: (
            not item[2],
            item[1] if item[1] is not None else float("inf"),
            -item[3],
            item[0].id,
        ),
    )

    ordered_intersections = [intersection for intersection, _, _, _ in ordered]
    priority_steps = [
        IntersectionPriorityStep(
            intersection_id=intersection.id,
            intersection_name=intersection.name,
            distance_km=distance,
            priority_phase="radius-first" if within_radius else "remaining",
        )
        for intersection, distance, within_radius, _ in ordered
    ]
    return ordered_intersections, priority_steps
