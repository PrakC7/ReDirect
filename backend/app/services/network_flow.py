from collections import defaultdict

from app.db.models import Intersection
from app.services.intersection_priority import (
    PRIORITY_RADIUS_KM,
    describe_directional_flow,
)


def build_network_flow_insights(
    intersections: list[Intersection],
    radius_km: float = PRIORITY_RADIUS_KM,
) -> dict[int, dict[str, float | str | int | None]]:
    insights: dict[int, dict[str, float | str | int | None]] = {}

    for target in intersections:
        nearby_vehicle_capacity = 0
        inbound_pressure_total = 0.0
        direction_weights: dict[str, float] = defaultdict(float)
        inbound_share_total = 0.0
        contributor_count = 0

        for source in intersections:
            if source.id == target.id:
                continue

            (
                distance,
                _movement_alignment,
                target_flow_direction,
                _dominant_flow_direction,
                approaching_zone,
                approaching_vehicle_share,
            ) = describe_directional_flow(source, target, intersections)
            if distance is None or distance > radius_km:
                continue

            nearby_vehicle_capacity += source.live_vehicle_count
            if not approaching_zone or not target_flow_direction:
                continue

            contributor_count += 1
            inbound_share_total += approaching_vehicle_share

            distance_weight = max(0.25, 1 - (distance / radius_km))
            contribution = (
                source.live_vehicle_count
                * approaching_vehicle_share
                * distance_weight
            )
            inbound_pressure_total += contribution
            direction_weights[target_flow_direction] += contribution

        incoming_pressure_score = round(
            min(
                inbound_pressure_total / max(nearby_vehicle_capacity, 1),
                1.0,
            ),
            2,
        )
        nearby_inbound_vehicle_share = round(
            inbound_share_total / max(contributor_count, 1),
            2,
        )

        insights[target.id] = {
            "incoming_pressure_score": incoming_pressure_score,
            "primary_inbound_direction": max(
                direction_weights,
                key=direction_weights.get,
                default=None,
            ),
            "nearby_inbound_vehicle_share": nearby_inbound_vehicle_share,
            "directional_contributors": contributor_count,
        }

    return insights
