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
)
from app.services.density import calculate_density_score, get_density_status
from app.services.emergency import EmergencyRequestStore, build_corridor
from app.services.optimization import build_signal_plan

router = APIRouter()
emergency_store = EmergencyRequestStore(settings.emergency_ttl_seconds)

SAMPLE_INTERSECTIONS = [
    Intersection(
        id=101,
        name="AIIMS Ring Road",
        zone="Central",
        lane_count=4,
        road_width_m=15.0,
        road_priority_weight=0.45,
        historical_congestion=0.88,
        live_vehicle_count=48,
        signal_group="North-South",
    ),
    Intersection(
        id=102,
        name="Lajpat Nagar Flyover",
        zone="South East",
        lane_count=3,
        road_width_m=13.5,
        road_priority_weight=0.32,
        historical_congestion=0.79,
        live_vehicle_count=41,
        signal_group="East-West",
    ),
    Intersection(
        id=103,
        name="ITO Junction",
        zone="Central",
        lane_count=5,
        road_width_m=16.5,
        road_priority_weight=0.55,
        historical_congestion=0.91,
        live_vehicle_count=63,
        signal_group="North-South",
    ),
    Intersection(
        id=104,
        name="Kashmere Gate ISBT",
        zone="North",
        lane_count=4,
        road_width_m=14.0,
        road_priority_weight=0.41,
        historical_congestion=0.74,
        live_vehicle_count=39,
        signal_group="East-West",
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


def _build_intersection_snapshots() -> list[IntersectionSnapshot]:
    state = _build_network_state()
    plan = build_signal_plan(state)
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
        snapshots.append(
            IntersectionSnapshot(
                id=intersection.id,
                name=intersection.name,
                zone=intersection.zone,
                signal_group=intersection.signal_group,
                live_vehicle_count=intersection.live_vehicle_count,
                density_score=density_score,
                priority_score=round(priority_score, 2),
                recommended_green_seconds=green_time,
                status=get_density_status(density_score),
            )
        )

    return snapshots


def _build_corridor_candidates() -> list[Intersection]:
    ranked_intersections = _build_intersection_snapshots()
    intersection_lookup = {intersection.id: intersection for intersection in SAMPLE_INTERSECTIONS}
    return [
        intersection_lookup[snapshot.id]
        for snapshot in ranked_intersections[:3]
    ]


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot() -> DashboardSnapshot:
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
        intersections=_build_intersection_snapshots(),
        active_requests=active_requests,
    )


@router.post(
    "/emergency/requests",
    response_model=EmergencyRequestRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_emergency_request(
    payload: EmergencyRequestCreate,
) -> EmergencyRequestRecord:
    corridor = build_corridor(_build_corridor_candidates(), payload.priority)
    return emergency_store.create(payload, corridor)


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
    corridor = build_corridor(_build_corridor_candidates(), payload.priority, alert.timestamp)
    return emergency_store.create(payload, corridor)
