from dataclasses import replace
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.db.models import Intersection
from app.schemas import (
    DashboardSnapshot,
    EmergencyRequestCreate,
    EmergencyRequestRecord,
    IntersectionSnapshot,
    LegacyEmergencyAlert,
    WrongWayViolationRecord,
)
from app.services.density import calculate_density_score, get_density_status
from app.services.emergency import EmergencyRequestStore, build_corridor
from app.services.intersection_priority import (
    PRIORITY_RADIUS_KM,
    build_intersection_priority_plan,
    resolve_anchor_intersection,
)
from app.services.network_flow import build_network_flow_insights
from app.services.optimization import build_signal_plan, calculate_priority_score
from app.services.rule_enforcement import build_wrong_way_enforcement

router = APIRouter()
emergency_store = EmergencyRequestStore(settings.emergency_ttl_seconds)

SAMPLE_INTERSECTIONS = [
    Intersection(
        id=101,
        name="AIIMS Ring Road",
        zone="Central",
        latitude=28.5674,
        longitude=77.2106,
        lane_count=4,
        road_width_m=15.0,
        road_priority_weight=0.45,
        historical_congestion=0.88,
        live_vehicle_count=48,
        signal_group="North-South",
        movement_profile={
            "northbound": 13,
            "southbound": 17,
            "eastbound": 8,
            "westbound": 10,
        },
        enforcement_camera_enabled=True,
        expected_flow_direction="southbound",
        enforcement_camera_quality="Existing high-definition ANPR camera",
    ),
    Intersection(
        id=102,
        name="Lajpat Nagar Flyover",
        zone="South East",
        latitude=28.5679,
        longitude=77.2432,
        lane_count=3,
        road_width_m=13.5,
        road_priority_weight=0.32,
        historical_congestion=0.79,
        live_vehicle_count=41,
        signal_group="East-West",
        movement_profile={
            "northbound": 6,
            "southbound": 4,
            "eastbound": 7,
            "westbound": 24,
        },
    ),
    Intersection(
        id=103,
        name="ITO Junction",
        zone="Central",
        latitude=28.6289,
        longitude=77.2411,
        lane_count=5,
        road_width_m=16.5,
        road_priority_weight=0.55,
        historical_congestion=0.91,
        live_vehicle_count=63,
        signal_group="North-South",
        movement_profile={
            "northbound": 9,
            "southbound": 8,
            "eastbound": 11,
            "westbound": 35,
        },
        enforcement_camera_enabled=True,
        expected_flow_direction="westbound",
        enforcement_camera_quality="Existing high-definition corridor camera",
    ),
    Intersection(
        id=104,
        name="Kashmere Gate ISBT",
        zone="North",
        latitude=28.6675,
        longitude=77.2278,
        lane_count=4,
        road_width_m=14.0,
        road_priority_weight=0.41,
        historical_congestion=0.74,
        live_vehicle_count=39,
        signal_group="East-West",
        movement_profile={
            "northbound": 4,
            "southbound": 20,
            "eastbound": 5,
            "westbound": 10,
        },
    ),
    Intersection(
        id=105,
        name="Manesar Toll Gate",
        zone="South West",
        latitude=28.3649,
        longitude=76.9424,
        lane_count=4,
        road_width_m=15.5,
        road_priority_weight=0.37,
        historical_congestion=0.69,
        live_vehicle_count=36,
        signal_group="North-South",
        movement_profile={
            "northbound": 16,
            "southbound": 5,
            "eastbound": 10,
            "westbound": 5,
        },
    ),
]


def _live_vehicle_count(base_count: int, offset: int) -> int:
    cycle = [-4, 0, 6, 10, 4, -2]
    current_minute = datetime.utcnow().minute
    adjustment = cycle[(current_minute + offset) % len(cycle)]
    return max(base_count + adjustment, 6)


def _build_network_state() -> list[tuple[Intersection, float, dict[str, int]]]:
    state: list[tuple[Intersection, float, dict[str, int]]] = []

    for index, intersection in enumerate(SAMPLE_INTERSECTIONS):
        live_count = _live_vehicle_count(intersection.live_vehicle_count, index)
        live_intersection = replace(intersection, live_vehicle_count=live_count)
        density_score = calculate_density_score(live_intersection)
        vehicle_distribution = {"bus": max(live_count // 20, 1)}
        state.append((live_intersection, density_score, vehicle_distribution))

    return state


def _build_priority_score_lookup(
    state: list[tuple[Intersection, float, dict[str, int]]],
    network_flow_insights: dict[int, dict[str, float | str | int | None]],
) -> dict[int, float]:
    return {
        intersection.id: calculate_priority_score(
            density_score,
            intersection.road_priority_weight,
            distribution,
            float(
                network_flow_insights[intersection.id]["incoming_pressure_score"]
            ),
        )
        for intersection, density_score, distribution in state
    }


def _build_live_network_context() -> tuple[
    list[tuple[Intersection, float, dict[str, int]]],
    list[Intersection],
    dict[int, dict[str, float | str | int | None]],
    dict[int, dict[str, object]],
    list[WrongWayViolationRecord],
    int,
]:
    state = _build_network_state()
    live_intersections = [intersection for intersection, _, _ in state]
    network_flow_insights = build_network_flow_insights(
        live_intersections,
        PRIORITY_RADIUS_KM,
    )
    wrong_way_by_intersection, wrong_way_alerts, enforcement_enabled_count = (
        build_wrong_way_enforcement(live_intersections)
    )
    return (
        state,
        live_intersections,
        network_flow_insights,
        wrong_way_by_intersection,
        wrong_way_alerts,
        enforcement_enabled_count,
    )


def _build_intersection_snapshots(
    state: list[tuple[Intersection, float, dict[str, int]]],
    network_flow_insights: dict[int, dict[str, float | str | int | None]],
    wrong_way_by_intersection: dict[int, dict[str, object]],
) -> list[IntersectionSnapshot]:
    directional_pressure_scores = {
        intersection_id: float(insight["incoming_pressure_score"])
        for intersection_id, insight in network_flow_insights.items()
    }
    plan = build_signal_plan(state, directional_pressure_scores)
    by_intersection_id = {
        intersection.id: intersection for intersection, _, _ in state
    }
    density_by_intersection = {
        intersection.id: density_score for intersection, density_score, _ in state
    }

    snapshots: list[IntersectionSnapshot] = []
    for intersection_id, _, priority_score, green_time in plan:
        intersection = by_intersection_id[intersection_id]
        density_score = density_by_intersection[intersection_id]
        network_insight = network_flow_insights[intersection_id]
        enforcement_insight = wrong_way_by_intersection[intersection_id]
        snapshots.append(
            IntersectionSnapshot(
                id=intersection.id,
                name=intersection.name,
                zone=intersection.zone,
                signal_group=intersection.signal_group,
                live_vehicle_count=intersection.live_vehicle_count,
                density_score=density_score,
                priority_score=round(priority_score, 2),
                incoming_pressure_score=float(
                    network_insight["incoming_pressure_score"]
                ),
                primary_inbound_direction=network_insight[
                    "primary_inbound_direction"
                ],
                nearby_inbound_vehicle_share=float(
                    network_insight["nearby_inbound_vehicle_share"]
                ),
                optional_enforcement_enabled=bool(
                    enforcement_insight["optional_enforcement_enabled"]
                ),
                expected_flow_direction=enforcement_insight[
                    "expected_flow_direction"
                ],
                wrong_way_alert_count=int(
                    enforcement_insight["wrong_way_alert_count"]
                ),
                wrong_way_vehicle_share=float(
                    enforcement_insight["wrong_way_vehicle_share"]
                ),
                recommended_green_seconds=green_time,
                status=get_density_status(density_score),
            )
        )

    return snapshots


def _build_corridor_plan_context(
    origin: str,
    destination: str,
) -> tuple[list[Intersection], list]:
    (
        state,
        live_intersections,
        network_flow_insights,
        _wrong_way_by_intersection,
        _wrong_way_alerts,
        _enforcement_enabled_count,
    ) = _build_live_network_context()
    priority_scores = _build_priority_score_lookup(state, network_flow_insights)
    anchor = resolve_anchor_intersection(
        f"{origin} {destination}",
        live_intersections,
    )
    ranked_intersections, priority_steps = build_intersection_priority_plan(
        anchor,
        live_intersections,
        priority_scores,
        PRIORITY_RADIUS_KM,
    )
    return ranked_intersections[:3], priority_steps


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot() -> DashboardSnapshot:
    (
        state,
        _live_intersections,
        network_flow_insights,
        wrong_way_by_intersection,
        wrong_way_alerts,
        enforcement_enabled_count,
    ) = _build_live_network_context()
    active_requests = emergency_store.list_active_summaries()
    average_clearance_gain = (
        round(
            sum(request.suggested_time_saved_minutes for request in active_requests)
            / len(active_requests)
        )
        if active_requests
        else 5
    )

    return DashboardSnapshot(
        generated_at=datetime.utcnow(),
        next_refresh_seconds=settings.signal_update_interval,
        active_emergency_count=len(active_requests),
        average_clearance_gain_minutes=average_clearance_gain,
        priority_radius_km=int(PRIORITY_RADIUS_KM),
        enforcement_enabled_intersections=enforcement_enabled_count,
        wrong_way_violation_count=len(wrong_way_alerts),
        optional_enforcement_note=(
            "Optional wrong-way enforcement is active only at selected "
            "locations where high-quality cameras are already installed."
        ),
        intersections=_build_intersection_snapshots(
            state,
            network_flow_insights,
            wrong_way_by_intersection,
        ),
        active_requests=active_requests,
        wrong_way_alerts=wrong_way_alerts,
    )


@router.post(
    "/emergency/requests",
    response_model=EmergencyRequestRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_emergency_request(
    payload: EmergencyRequestCreate,
) -> EmergencyRequestRecord:
    ranked_intersections, priority_steps = _build_corridor_plan_context(
        payload.origin,
        payload.destination,
    )
    priority_lookup = {
        step.intersection_id: step for step in priority_steps
    }
    corridor = build_corridor(
        ranked_intersections,
        payload.priority,
        intersection_priorities=priority_lookup,
    )
    return emergency_store.create(
        payload,
        corridor,
        int(PRIORITY_RADIUS_KM),
        priority_steps,
    )


@router.get("/emergency/requests", response_model=list[EmergencyRequestRecord])
def list_emergency_requests() -> list[EmergencyRequestRecord]:
    return emergency_store.list_active()


@router.get("/gov/emergency/active", response_model=list[EmergencyRequestRecord])
def list_active_emergencies(
    x_api_key: str = Header(...),
) -> list[EmergencyRequestRecord]:
    if x_api_key != settings.gov_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    return emergency_store.list_active()


@router.get(
    "/gov/violations/wrong-way",
    response_model=list[WrongWayViolationRecord],
)
def list_wrong_way_violations(
    x_api_key: str = Header(...),
) -> list[WrongWayViolationRecord]:
    if x_api_key != settings.gov_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    (
        _state,
        _live_intersections,
        _network_flow_insights,
        _wrong_way_by_intersection,
        wrong_way_alerts,
        _enforcement_enabled_count,
    ) = _build_live_network_context()
    return wrong_way_alerts


@router.post(
    "/emergency/alert",
    response_model=EmergencyRequestRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_legacy_alert(alert: LegacyEmergencyAlert) -> EmergencyRequestRecord:
    payload = EmergencyRequestCreate(
        requester_name="Automated camera alert",
        department="Road control room",
        vehicle_type=alert.type,
        purpose="Vision-triggered emergency priority",
        origin=alert.location,
        destination="Nearest critical corridor",
        return_destination=None,
        vehicle_id_type="Alert ID",
        vehicle_id=str(alert.id),
        priority="Critical",
        estimated_travel_minutes=12,
        route_notes="Generated from the legacy emergency alert endpoint.",
    )
    ranked_intersections, priority_steps = _build_corridor_plan_context(
        payload.origin,
        payload.destination,
    )
    priority_lookup = {
        step.intersection_id: step for step in priority_steps
    }
    corridor = build_corridor(
        ranked_intersections,
        payload.priority,
        alert.timestamp,
        priority_lookup,
    )
    return emergency_store.create(
        payload,
        corridor,
        int(PRIORITY_RADIUS_KM),
        priority_steps,
    )
