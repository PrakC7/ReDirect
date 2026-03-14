from dataclasses import replace
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.db.models import Intersection
from app.schemas import (
    DashboardSnapshot,
    DirectionalCountCodePacketIn,
    EmergencyApprovalRequest,
    EmergencyRequestCreate,
    EmergencyRequestRecord,
    EmergencyRouteSuggestion,
    IntersectionSnapshot,
    LegacyEmergencyAlert,
    TelemetryIngestResponse,
    TelemetrySummaryIn,
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
from app.services.prototype_state import PrototypeStateStore
from app.services.route_network import nearest_intersection, shortest_distance_km, shortest_path
from app.services.rule_enforcement import build_wrong_way_enforcement

router = APIRouter()
prototype_state = PrototypeStateStore()
emergency_store = EmergencyRequestStore(
    settings.emergency_ttl_seconds,
    prototype_state,
)

CARDINAL_DIRECTIONS = (
    "northbound",
    "southbound",
    "eastbound",
    "westbound",
)
EMERGENCY_VEHICLE_TYPES = {
    "ambulance",
    "fire brigade",
    "fire truck",
    "police",
    "disaster response",
}

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
        movement_profile={"northbound": 13, "southbound": 17, "eastbound": 8, "westbound": 10},
        vehicle_distribution_profile={"car": 20, "bus": 3, "bike": 14, "auto": 11},
        location_aliases=("aiims trauma centre", "safdarjung hospital", "green park"),
        road_links_km={102: 4.2, 103: 8.5, 105: 34.0},
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
        movement_profile={"northbound": 6, "southbound": 4, "eastbound": 7, "westbound": 24},
        vehicle_distribution_profile={"car": 17, "bus": 1, "bike": 15, "auto": 8},
        location_aliases=("lajpat nagar", "ashram chowk", "nehru place corridor"),
        road_links_km={101: 4.2, 103: 7.1, 104: 14.5, 105: 36.5},
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
        movement_profile={"northbound": 9, "southbound": 8, "eastbound": 11, "westbound": 35},
        vehicle_distribution_profile={"car": 25, "bus": 4, "bike": 14, "auto": 12, "truck": 8},
        location_aliases=("ito", "delhi secretariat", "rajghat corridor"),
        road_links_km={101: 8.5, 102: 7.1, 104: 5.0},
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
        movement_profile={"northbound": 4, "southbound": 20, "eastbound": 5, "westbound": 10},
        vehicle_distribution_profile={"car": 13, "bus": 6, "bike": 8, "auto": 12},
        location_aliases=("kashmere gate", "kashmiri gate", "isbt"),
        road_links_km={102: 14.5, 103: 5.0},
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
        movement_profile={"northbound": 16, "southbound": 5, "eastbound": 10, "westbound": 5},
        vehicle_distribution_profile={"car": 16, "bus": 0, "bike": 10, "auto": 4, "truck": 6},
        location_aliases=("manesar", "gurugram", "medanta hospital", "fortis gurgaon", "hero honda chowk"),
        road_links_km={101: 34.0, 102: 36.5},
    ),
]


def _intersection_lookup() -> dict[int, Intersection]:
    return {intersection.id: intersection for intersection in SAMPLE_INTERSECTIONS}


def _scale_counts(profile: dict[str, int], target_total: int) -> dict[str, int]:
    if not profile or target_total <= 0:
        return {}

    normalized = {key: max(int(value), 0) for key, value in profile.items()}
    base_total = sum(normalized.values())
    if base_total <= 0:
        return {}

    scaled = {}
    remainders = []
    assigned = 0
    for key, value in normalized.items():
        raw_value = target_total * (value / base_total)
        base_value = int(raw_value)
        scaled[key] = base_value
        assigned += base_value
        remainders.append((raw_value - base_value, key))

    for _fraction, key in sorted(remainders, reverse=True)[: max(target_total - assigned, 0)]:
        scaled[key] += 1

    return {key: value for key, value in scaled.items() if value > 0}


def _normalize_directional_counts(
    directional_counts: dict[str, int],
    fallback_total: int,
) -> dict[str, int]:
    normalized = {
        direction: max(int(count), 0)
        for direction, count in directional_counts.items()
        if direction in CARDINAL_DIRECTIONS and int(count) >= 0
    }
    if normalized:
        return normalized
    if fallback_total <= 0:
        return {}

    evenly_distributed = fallback_total // len(CARDINAL_DIRECTIONS)
    remainder = fallback_total % len(CARDINAL_DIRECTIONS)
    generated = {}
    for index, direction in enumerate(CARDINAL_DIRECTIONS):
        generated[direction] = evenly_distributed + (1 if index < remainder else 0)
    return generated


def _live_vehicle_count(base_count: int, offset: int) -> int:
    cycle = [-4, 0, 6, 10, 4, -2]
    current_minute = datetime.utcnow().minute
    adjustment = cycle[(current_minute + offset) % len(cycle)]
    return max(base_count + adjustment, 6)


def _fresh_telemetry_map() -> dict[int, dict[str, object]]:
    cutoff = datetime.utcnow() - timedelta(seconds=settings.telemetry_freshness_seconds)
    fresh = {}
    for intersection_id, reading in prototype_state.load_telemetry().items():
        captured_at_raw = reading.get("captured_at")
        if not isinstance(captured_at_raw, str):
            continue
        captured_at = datetime.fromisoformat(captured_at_raw)
        if captured_at < cutoff:
            continue
        fresh[intersection_id] = reading
    return fresh


def _decode_directional_count_packet(payload: DirectionalCountCodePacketIn) -> dict[str, object]:
    directional_vehicle_count = {}
    average_speed_by_direction = {}
    weighted_speed_total = 0.0
    weighted_vehicle_total = 0

    for flow in payload.flows:
        upper_bound = flow.vehicle_count_code * payload.count_unit_size
        if upper_bound and flow.separate_vehicle_count == 0:
            estimated_vehicle_count = max(upper_bound - 1, 1)
        else:
            estimated_vehicle_count = upper_bound + flow.separate_vehicle_count

        average_speed_kph = round(flow.average_speed_kph_x10 / 10, 1)
        directional_vehicle_count[flow.direction] = estimated_vehicle_count
        average_speed_by_direction[flow.direction] = average_speed_kph
        weighted_speed_total += estimated_vehicle_count * average_speed_kph
        weighted_vehicle_total += estimated_vehicle_count

    return {
        "captured_at": datetime.utcfromtimestamp(payload.captured_epoch).isoformat(),
        "vehicle_count": sum(directional_vehicle_count.values()),
        "occupancy_index": round(min(sum(directional_vehicle_count.values()) / 120.0, 1.0), 2),
        "directional_vehicle_count": directional_vehicle_count,
        "vehicle_type_distribution": {},
        "average_speed_by_direction": average_speed_by_direction,
        "average_speed_kph": round(weighted_speed_total / max(weighted_vehicle_total, 1), 1),
        "emergency_detected": bool(payload.emergency_flag),
        "wrong_way_count": int(payload.wrong_way_count),
    }


def _store_telemetry_reading(intersection_id: int, reading: dict[str, object]) -> TelemetryIngestResponse:
    if intersection_id not in _intersection_lookup():
        raise HTTPException(status_code=404, detail="Intersection not found")

    captured_at_raw = reading.get("captured_at")
    captured_at = (
        datetime.fromisoformat(captured_at_raw)
        if isinstance(captured_at_raw, str)
        else datetime.utcnow()
    )
    directional_counts = _normalize_directional_counts(
        reading.get("directional_vehicle_count", {}),
        int(reading.get("vehicle_count", 0)),
    )
    vehicle_count = sum(directional_counts.values()) or int(reading.get("vehicle_count", 0))
    vehicle_distribution = _scale_counts(
        {
            vehicle_type: int(count)
            for vehicle_type, count in reading.get("vehicle_type_distribution", {}).items()
        },
        vehicle_count,
    )
    average_speed_by_direction = {
        direction: round(float(speed_kph), 1)
        for direction, speed_kph in reading.get("average_speed_by_direction", {}).items()
        if direction in CARDINAL_DIRECTIONS
    }
    average_speed_kph = reading.get("average_speed_kph")
    if average_speed_kph is None and average_speed_by_direction:
        average_speed_kph = round(
            sum(average_speed_by_direction.values()) / len(average_speed_by_direction),
            1,
        )

    prototype_state.upsert_telemetry(
        intersection_id,
        {
            "captured_at": captured_at.isoformat(),
            "vehicle_count": vehicle_count,
            "occupancy_index": round(float(reading.get("occupancy_index", 0.0)), 2),
            "directional_vehicle_count": directional_counts,
            "vehicle_type_distribution": vehicle_distribution,
            "average_speed_by_direction": average_speed_by_direction,
            "average_speed_kph": round(float(average_speed_kph or 0.0), 1),
            "emergency_detected": bool(reading.get("emergency_detected", False)),
            "wrong_way_count": int(reading.get("wrong_way_count", 0)),
            "data_source": "edge-telemetry",
        },
    )

    return TelemetryIngestResponse(
        intersection_id=intersection_id,
        data_source="edge-telemetry",
        captured_at=captured_at,
        vehicle_count=vehicle_count,
        status="Telemetry accepted",
    )


def _build_network_state():
    telemetry_by_intersection = _fresh_telemetry_map()
    state = []

    for index, intersection in enumerate(SAMPLE_INTERSECTIONS):
        reading = telemetry_by_intersection.get(intersection.id)
        if reading:
            live_count = int(reading["vehicle_count"])
            movement_profile = reading.get("directional_vehicle_count") or _scale_counts(
                intersection.movement_profile,
                live_count,
            )
            vehicle_distribution = reading.get("vehicle_type_distribution") or _scale_counts(
                intersection.vehicle_distribution_profile,
                live_count,
            )
            data_source = "edge-telemetry"
            last_telemetry_at = datetime.fromisoformat(str(reading["captured_at"]))
        else:
            live_count = _live_vehicle_count(intersection.live_vehicle_count, index)
            movement_profile = _scale_counts(intersection.movement_profile, live_count)
            vehicle_distribution = _scale_counts(
                intersection.vehicle_distribution_profile,
                live_count,
            )
            data_source = "prototype-simulation"
            last_telemetry_at = None

        live_intersection = replace(
            intersection,
            live_vehicle_count=live_count,
            movement_profile=movement_profile,
            vehicle_distribution_profile=vehicle_distribution,
        )
        density_score = calculate_density_score(live_intersection)
        state.append(
            (
                live_intersection,
                density_score,
                vehicle_distribution,
                data_source,
                last_telemetry_at,
            )
        )

    return state


def _build_priority_score_lookup(state, network_flow_insights):
    return {
        intersection.id: calculate_priority_score(
            density_score,
            intersection.road_priority_weight,
            distribution,
            float(network_flow_insights[intersection.id]["incoming_pressure_score"]),
        )
        for intersection, density_score, distribution, _data_source, _captured_at in state
    }


def _build_live_network_context():
    state = _build_network_state()
    live_intersections = [intersection for intersection, *_rest in state]
    network_flow_insights = build_network_flow_insights(
        live_intersections,
        PRIORITY_RADIUS_KM,
    )
    wrong_way_by_intersection, wrong_way_alerts, enforcement_enabled_count = (
        build_wrong_way_enforcement(live_intersections)
    )
    prototype_state.save_wrong_way_alerts(
        [alert.model_dump(mode="json") for alert in wrong_way_alerts]
    )
    live_telemetry_count = sum(
        1
        for _intersection, _density, _distribution, data_source, _captured_at in state
        if data_source == "edge-telemetry"
    )
    return (
        state,
        live_intersections,
        network_flow_insights,
        wrong_way_by_intersection,
        wrong_way_alerts,
        enforcement_enabled_count,
        live_telemetry_count,
    )


def _build_intersection_snapshots(state, network_flow_insights, wrong_way_by_intersection):
    directional_pressure_scores = {
        intersection_id: float(insight["incoming_pressure_score"])
        for intersection_id, insight in network_flow_insights.items()
    }
    plan = build_signal_plan(
        [
            (intersection, density_score, distribution)
            for intersection, density_score, distribution, _data_source, _captured_at in state
        ],
        directional_pressure_scores,
    )
    by_intersection_id = {intersection.id: intersection for intersection, *_rest in state}
    density_by_intersection = {
        intersection.id: density_score
        for intersection, density_score, _distribution, _data_source, _captured_at in state
    }
    source_by_intersection = {
        intersection.id: data_source
        for intersection, _density_score, _distribution, data_source, _captured_at in state
    }
    telemetry_time_by_intersection = {
        intersection.id: captured_at
        for intersection, _density_score, _distribution, _data_source, captured_at in state
    }

    snapshots = []
    for intersection_id, _density, priority_score, green_time in plan:
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
                incoming_pressure_score=float(network_insight["incoming_pressure_score"]),
                primary_inbound_direction=network_insight["primary_inbound_direction"],
                nearby_inbound_vehicle_share=float(network_insight["nearby_inbound_vehicle_share"]),
                optional_enforcement_enabled=bool(enforcement_insight["optional_enforcement_enabled"]),
                expected_flow_direction=enforcement_insight["expected_flow_direction"],
                wrong_way_alert_count=int(enforcement_insight["wrong_way_alert_count"]),
                wrong_way_vehicle_share=float(enforcement_insight["wrong_way_vehicle_share"]),
                recommended_green_seconds=green_time,
                data_source=source_by_intersection[intersection_id],
                last_telemetry_at=telemetry_time_by_intersection[intersection_id],
                status=get_density_status(density_score),
            )
        )

    return snapshots


def _ensure_verified_location(latitude, longitude, intersections, location_label):
    anchor, anchor_distance = nearest_intersection(
        latitude,
        longitude,
        intersections,
        settings.location_match_radius_km,
    )
    if anchor is None or anchor_distance is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{location_label} must be shared from device GPS or a map app "
                "within the prototype network before an emergency request can be submitted."
            ),
        )
    return anchor


def _estimate_path_distance(intersections, path):
    if len(path) <= 1:
        return 0.0

    total_distance = 0.0
    for first, second in zip(path, path[1:]):
        segment_distance = shortest_distance_km(intersections, first.id, second.id)
        total_distance += float(segment_distance or 0.0)
    return round(total_distance, 1)


def _candidate_route_paths(intersections, origin_anchor, destination_anchor):
    candidates = {}

    base_path = shortest_path(intersections, origin_anchor.id, destination_anchor.id)
    if base_path:
        candidates[tuple(intersection.id for intersection in base_path)] = base_path

    for via in intersections:
        if via.id in {origin_anchor.id, destination_anchor.id}:
            continue
        first_leg = shortest_path(intersections, origin_anchor.id, via.id)
        second_leg = shortest_path(intersections, via.id, destination_anchor.id)
        if not first_leg or not second_leg:
            continue

        combined = first_leg + second_leg[1:]
        combined_ids = tuple(intersection.id for intersection in combined)
        if len(combined_ids) != len(set(combined_ids)):
            continue
        candidates[combined_ids] = combined

    return list(candidates.values())


def _build_route_suggestions(
    intersections,
    origin_anchor,
    destination_anchor,
    priority_scores,
    estimated_travel_minutes,
):
    candidate_paths = _candidate_route_paths(
        intersections,
        origin_anchor,
        destination_anchor,
    )
    if not candidate_paths:
        candidate_paths = [[origin_anchor, destination_anchor]]

    base_shortest_route = tuple(
        intersection.id
        for intersection in shortest_path(intersections, origin_anchor.id, destination_anchor.id)
    )
    ranked_routes = []
    for path in candidate_paths:
        route_ids = tuple(intersection.id for intersection in path)
        total_distance = _estimate_path_distance(intersections, path)
        congestion_score = round(
            sum(priority_scores.get(intersection.id, 0.0) for intersection in path)
            / max(len(path), 1),
            2,
        )
        route_cost = round((congestion_score * 2.4) + (total_distance / 12.0), 2)
        ranked_routes.append((route_cost, total_distance, congestion_score, route_ids, path))

    ranked_routes.sort(key=lambda item: (item[0], item[1], len(item[4])))
    suggestions = []
    for index, (_route_cost, total_distance, congestion_score, route_ids, path) in enumerate(ranked_routes[:2]):
        if index == 0 and route_ids != base_shortest_route:
            reason = (
                "A clearer alternate corridor is recommended because the shortest path "
                "is carrying heavier live pressure right now."
            )
        elif index == 0:
            reason = "This is the shortest usable corridor under the current live pressure."
        else:
            reason = (
                "Fallback corridor if the primary path degrades or a control-room "
                "operator prefers a secondary option."
            )

        suggestions.append(
            EmergencyRouteSuggestion(
                route_id="route-" + "-".join(str(intersection_id) for intersection_id in route_ids),
                label="Primary corridor" if index == 0 else "Alternate corridor",
                reason=reason,
                total_distance_km=total_distance,
                estimated_travel_minutes=max(
                    estimated_travel_minutes + int(round(congestion_score)),
                    len(path) * 2,
                ),
                congestion_score=congestion_score,
                intersections=[intersection.name for intersection in path],
            )
        )

    return suggestions


def _route_ids_from_suggestion(route_id: str) -> list[int]:
    if not route_id.startswith("route-"):
        raise HTTPException(status_code=422, detail="Invalid route selection")
    try:
        return [int(intersection_id) for intersection_id in route_id[6:].split("-") if intersection_id]
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Invalid route selection") from error


def _target_corridor_size(estimated_travel_minutes: int) -> int:
    return min(
        max((estimated_travel_minutes // 4) + 2, 3),
        settings.corridor_max_intersections,
    )


def _build_route_request_context(payload: EmergencyRequestCreate):
    (
        state,
        live_intersections,
        network_flow_insights,
        _wrong_way_by_intersection,
        _wrong_way_alerts,
        _enforcement_enabled_count,
        _live_telemetry_count,
    ) = _build_live_network_context()
    priority_scores = _build_priority_score_lookup(state, network_flow_insights)

    origin_anchor = _ensure_verified_location(
        payload.origin_latitude,
        payload.origin_longitude,
        live_intersections,
        "Origin location",
    )
    destination_anchor = _ensure_verified_location(
        payload.destination_latitude,
        payload.destination_longitude,
        live_intersections,
        "Destination location",
    )

    route_suggestions = _build_route_suggestions(
        live_intersections,
        origin_anchor,
        destination_anchor,
        priority_scores,
        payload.estimated_travel_minutes,
    )
    primary_route_ids = set(_route_ids_from_suggestion(route_suggestions[0].route_id))
    _, priority_steps = build_intersection_priority_plan(
        destination_anchor,
        live_intersections,
        priority_scores,
        PRIORITY_RADIUS_KM,
        primary_route_ids,
    )

    route_lookup = {intersection.id: intersection for intersection in live_intersections}
    selected_route = [
        route_lookup[intersection_id]
        for intersection_id in _route_ids_from_suggestion(route_suggestions[0].route_id)
        if intersection_id in route_lookup
    ]
    selected_route = selected_route[: _target_corridor_size(payload.estimated_travel_minutes)]
    return route_suggestions, selected_route, priority_steps


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
        live_telemetry_count,
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
        live_telemetry_intersections=live_telemetry_count,
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
    "/telemetry/summary",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_summary_telemetry(payload: TelemetrySummaryIn) -> TelemetryIngestResponse:
    captured_at = payload.captured_at or datetime.utcnow()
    return _store_telemetry_reading(
        payload.intersection_id,
        {
            "captured_at": captured_at.isoformat(),
            "vehicle_count": payload.vehicle_count,
            "occupancy_index": payload.occupancy_index,
            "directional_vehicle_count": payload.directional_vehicle_count,
            "vehicle_type_distribution": payload.vehicle_type_distribution,
            "average_speed_by_direction": payload.average_speed_by_direction,
            "average_speed_kph": payload.average_speed_kph,
            "emergency_detected": payload.emergency_detected,
            "wrong_way_count": payload.wrong_way_count,
        },
    )


@router.post(
    "/telemetry/count-codes",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_count_code_telemetry(
    payload: DirectionalCountCodePacketIn,
) -> TelemetryIngestResponse:
    return _store_telemetry_reading(
        payload.intersection_id,
        _decode_directional_count_packet(payload),
    )


@router.post(
    "/emergency/requests",
    response_model=EmergencyRequestRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_emergency_request(
    payload: EmergencyRequestCreate,
) -> EmergencyRequestRecord:
    if payload.return_destination and (
        payload.return_destination_latitude is None
        or payload.return_destination_longitude is None
        or payload.return_destination_location_source is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Return destination must also come from GPS or a map-picked "
                "location when it is provided."
            ),
        )

    if payload.vehicle_type.lower() not in EMERGENCY_VEHICLE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Only approved emergency vehicles can request signal-priority routing.",
        )

    route_suggestions, _selected_route, priority_steps = _build_route_request_context(payload)
    return emergency_store.create(
        payload,
        route_suggestions,
        int(PRIORITY_RADIUS_KM),
        priority_steps,
    )


@router.post(
    "/emergency/requests/{request_id}/approve",
    response_model=EmergencyRequestRecord,
)
def approve_emergency_request(
    request_id: str,
    payload: EmergencyApprovalRequest,
    x_api_key: str = Header(...),
) -> EmergencyRequestRecord:
    if x_api_key != settings.gov_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        record = emergency_store.get(request_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Emergency request not found") from error

    if payload.route_id not in {suggestion.route_id for suggestion in record.route_suggestions}:
        raise HTTPException(
            status_code=422,
            detail="Selected route is not part of the pending request options.",
        )

    (
        state,
        live_intersections,
        network_flow_insights,
        _wrong_way_by_intersection,
        _wrong_way_alerts,
        _enforcement_enabled_count,
        _live_telemetry_count,
    ) = _build_live_network_context()
    priority_scores = _build_priority_score_lookup(state, network_flow_insights)
    route_lookup = {intersection.id: intersection for intersection in live_intersections}
    selected_route_ids = _route_ids_from_suggestion(payload.route_id)
    selected_route = [
        route_lookup[intersection_id]
        for intersection_id in selected_route_ids
        if intersection_id in route_lookup
    ]
    if not selected_route:
        raise HTTPException(
            status_code=422,
            detail="No intersections were resolved for the approved route.",
        )

    destination_anchor = selected_route[-1]
    _, priority_steps = build_intersection_priority_plan(
        destination_anchor,
        live_intersections,
        priority_scores,
        PRIORITY_RADIUS_KM,
        set(selected_route_ids),
    )
    priority_lookup = {step.intersection_id: step for step in priority_steps}
    corridor = build_corridor(
        selected_route,
        record.priority,
        intersection_priorities=priority_lookup,
    )

    try:
        return emergency_store.approve(
            request_id,
            payload,
            corridor,
            priority_steps,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Emergency request not found") from error


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
    stored_alerts = prototype_state.load_wrong_way_alerts()
    if stored_alerts:
        return [
            WrongWayViolationRecord.model_validate(alert)
            for alert in stored_alerts
        ]
    (
        _state,
        _live_intersections,
        _network_flow_insights,
        _wrong_way_by_intersection,
        wrong_way_alerts,
        _enforcement_enabled_count,
        _live_telemetry_count,
    ) = _build_live_network_context()
    return wrong_way_alerts


@router.post(
    "/emergency/alert",
    response_model=EmergencyRequestRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_legacy_alert(alert: LegacyEmergencyAlert) -> EmergencyRequestRecord:
    anchor = resolve_anchor_intersection(alert.location, SAMPLE_INTERSECTIONS)
    if anchor is None:
        raise HTTPException(
            status_code=422,
            detail="Legacy alert location could not be matched to the prototype network.",
        )

    payload = EmergencyRequestCreate(
        requester_name="Automated camera alert",
        department="Road control room",
        vehicle_type=alert.type,
        purpose="Vision-triggered emergency priority",
        origin=anchor.name,
        origin_latitude=anchor.latitude,
        origin_longitude=anchor.longitude,
        origin_location_source="maps-picked",
        destination=anchor.name,
        destination_latitude=anchor.latitude,
        destination_longitude=anchor.longitude,
        destination_location_source="maps-picked",
        return_destination=None,
        return_destination_latitude=None,
        return_destination_longitude=None,
        return_destination_location_source=None,
        vehicle_id_type="Alert ID",
        vehicle_id=str(alert.id),
        priority="Critical",
        estimated_travel_minutes=12,
        route_notes="Generated from the legacy emergency alert endpoint.",
    )
    route_suggestions, _selected_route, priority_steps = _build_route_request_context(payload)
    return emergency_store.create(
        payload,
        route_suggestions,
        int(PRIORITY_RADIUS_KM),
        priority_steps,
    )
