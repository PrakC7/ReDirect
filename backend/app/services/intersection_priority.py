from math import asin, atan2, cos, degrees, radians, sin, sqrt

from app.db.models import Intersection
from app.schemas import IntersectionPriorityStep
from app.services.route_network import shortest_distance_km

PRIORITY_RADIUS_KM = 20.0
CARDINAL_BEARINGS = {
    "northbound": 0.0,
    "eastbound": 90.0,
    "southbound": 180.0,
    "westbound": 270.0,
}
ALIGNMENT_PRIORITY = {
    "at-zone": 4,
    "towards-zone": 3,
    "cross-traffic": 2,
    "away-from-zone": 1,
    "undetermined": 0,
}


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


def bearing_degrees(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    first_lat = radians(first_latitude)
    second_lat = radians(second_latitude)
    lon_delta = radians(second_longitude - first_longitude)

    y_axis = sin(lon_delta) * cos(second_lat)
    x_axis = (
        cos(first_lat) * sin(second_lat)
        - sin(first_lat) * cos(second_lat) * cos(lon_delta)
    )
    return (degrees(atan2(y_axis, x_axis)) + 360.0) % 360.0


def _bearing_delta(first_bearing: float, second_bearing: float) -> float:
    raw_delta = abs(first_bearing - second_bearing)
    return min(raw_delta, 360.0 - raw_delta)


def _nearest_direction_label(target_bearing: float) -> str:
    return min(
        CARDINAL_BEARINGS,
        key=lambda direction: _bearing_delta(
            CARDINAL_BEARINGS[direction],
            target_bearing,
        ),
    )


def _movement_alignment_details(
    intersection: Intersection,
    target_bearing: float | None,
    anchor_distance: float | None,
) -> tuple[str, str | None, str | None, bool, float]:
    if anchor_distance == 0:
        dominant_flow_direction = max(
            intersection.movement_profile,
            key=intersection.movement_profile.get,
            default=None,
        )
        return "at-zone", None, dominant_flow_direction, True, 1.0

    dominant_flow_direction = max(
        intersection.movement_profile,
        key=intersection.movement_profile.get,
        default=None,
    )
    if target_bearing is None or not intersection.movement_profile:
        return "undetermined", None, dominant_flow_direction, False, 0.0

    toward_zone = 0
    cross_traffic = 0
    away_from_zone = 0
    total_flow = sum(intersection.movement_profile.values()) or 1

    for direction, vehicle_count in intersection.movement_profile.items():
        direction_bearing = CARDINAL_BEARINGS[direction]
        bearing_gap = _bearing_delta(direction_bearing, target_bearing)

        if bearing_gap <= 45:
            toward_zone += vehicle_count
        elif bearing_gap >= 135:
            away_from_zone += vehicle_count
        else:
            cross_traffic += vehicle_count

    approaching_vehicle_share = round(toward_zone / total_flow, 2)
    target_flow_direction = _nearest_direction_label(target_bearing)

    if toward_zone >= max(cross_traffic, away_from_zone) and toward_zone > 0:
        return (
            "towards-zone",
            target_flow_direction,
            dominant_flow_direction,
            True,
            approaching_vehicle_share,
        )
    if away_from_zone > max(cross_traffic, toward_zone):
        return (
            "away-from-zone",
            target_flow_direction,
            dominant_flow_direction,
            False,
            approaching_vehicle_share,
        )
    if cross_traffic > 0:
        return (
            "cross-traffic",
            target_flow_direction,
            dominant_flow_direction,
            False,
            approaching_vehicle_share,
        )
    return (
        "undetermined",
        target_flow_direction,
        dominant_flow_direction,
        False,
        approaching_vehicle_share,
    )


def describe_directional_flow(
    source: Intersection,
    target: Intersection | None,
    network_intersections: list[Intersection] | None = None,
) -> tuple[float | None, str, str | None, str | None, bool, float]:
    if target is None:
        dominant_flow_direction = max(
            source.movement_profile,
            key=source.movement_profile.get,
            default=None,
        )
        return None, "undetermined", None, dominant_flow_direction, False, 0.0

    road_distance = (
        shortest_distance_km(network_intersections, source.id, target.id)
        if network_intersections
        else None
    )
    target_distance = road_distance
    if target_distance is None:
        target_distance = round(
            distance_km(
                source.latitude,
                source.longitude,
                target.latitude,
                target.longitude,
            ),
            1,
        )
    target_bearing = None
    if target_distance != 0:
        target_bearing = bearing_degrees(
            source.latitude,
            source.longitude,
            target.latitude,
            target.longitude,
        )

    (
        movement_alignment,
        target_flow_direction,
        dominant_flow_direction,
        approaching_zone,
        approaching_vehicle_share,
    ) = _movement_alignment_details(source, target_bearing, target_distance)
    return (
        target_distance,
        movement_alignment,
        target_flow_direction,
        dominant_flow_direction,
        approaching_zone,
        approaching_vehicle_share,
    )


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
            *[alias.lower() for alias in intersection.location_aliases],
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
    resolved_route_ids: set[int] | None = None,
) -> tuple[list[Intersection], list[IntersectionPriorityStep]]:
    ranked: list[
        tuple[
            Intersection,
            float | None,
            float | None,
            bool,
            bool,
            float,
            str,
            str | None,
            str | None,
            bool,
            float,
        ]
    ] = []

    route_ids = resolved_route_ids or set()

    for intersection in intersections:
        (
            anchor_distance,
            movement_alignment,
            target_flow_direction,
            dominant_flow_direction,
            approaching_zone,
            approaching_vehicle_share,
        ) = describe_directional_flow(
            intersection,
            anchor,
            intersections,
        )
        within_radius = (
            anchor_distance is not None and anchor_distance <= radius_km
        )
        road_distance = (
            shortest_distance_km(intersections, intersection.id, anchor.id)
            if anchor is not None
            else None
        )

        ranked.append(
            (
                intersection,
                anchor_distance,
                road_distance,
                within_radius,
                intersection.id in route_ids,
                priority_scores.get(intersection.id, 0.0),
                movement_alignment,
                target_flow_direction,
                dominant_flow_direction,
                approaching_zone,
                approaching_vehicle_share,
            )
        )

    ordered = sorted(
        ranked,
        key=lambda item: (
            not item[3],
            not item[4],
            -ALIGNMENT_PRIORITY[item[6]],
            item[2] if item[2] is not None else (
                item[1] if item[1] is not None else float("inf")
            ),
            -item[10],
            -item[5],
            item[0].id,
        ),
    )

    ordered_intersections = [intersection for intersection, *_ in ordered]
    priority_steps = [
        IntersectionPriorityStep(
            intersection_id=intersection.id,
            intersection_name=intersection.name,
            distance_km=distance,
            road_distance_km=road_distance,
            priority_phase="radius-first" if within_radius else "remaining",
            target_flow_direction=target_flow_direction,
            dominant_flow_direction=dominant_flow_direction,
            approaching_zone=approaching_zone,
            approaching_vehicle_share=approaching_vehicle_share,
            on_resolved_route=on_resolved_route,
            movement_alignment=movement_alignment,
        )
        for (
            intersection,
            distance,
            road_distance,
            within_radius,
            on_resolved_route,
            _priority_score,
            movement_alignment,
            target_flow_direction,
            dominant_flow_direction,
            approaching_zone,
            approaching_vehicle_share,
        ) in ordered
    ]
    return ordered_intersections, priority_steps
