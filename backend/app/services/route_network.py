from __future__ import annotations

from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt

from app.db.models import Intersection


def haversine_distance_km(
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


def nearest_intersection(
    latitude: float,
    longitude: float,
    intersections: list[Intersection],
    max_distance_km: float,
) -> tuple[Intersection | None, float | None]:
    best_match: tuple[Intersection, float] | None = None

    for intersection in intersections:
        distance = haversine_distance_km(
            latitude,
            longitude,
            intersection.latitude,
            intersection.longitude,
        )
        if best_match is None or distance < best_match[1]:
            best_match = (intersection, distance)

    if best_match is None or best_match[1] > max_distance_km:
        return None, None
    return best_match


def _build_graph(intersections: list[Intersection]) -> dict[int, dict[int, float]]:
    graph: dict[int, dict[int, float]] = {intersection.id: {} for intersection in intersections}

    for intersection in intersections:
        for neighbor_id, distance_km in intersection.road_links_km.items():
            graph[intersection.id][neighbor_id] = distance_km
            graph.setdefault(neighbor_id, {})
            current = graph[neighbor_id].get(intersection.id)
            if current is None or distance_km < current:
                graph[neighbor_id][intersection.id] = distance_km

    return graph


def shortest_path_ids(
    intersections: list[Intersection],
    origin_id: int,
    destination_id: int,
) -> list[int]:
    if origin_id == destination_id:
        return [origin_id]

    graph = _build_graph(intersections)
    queue: list[tuple[float, int]] = [(0.0, origin_id)]
    distances = {origin_id: 0.0}
    previous: dict[int, int] = {}

    while queue:
        current_distance, current_id = heappop(queue)
        if current_id == destination_id:
            break
        if current_distance > distances.get(current_id, float("inf")):
            continue

        for neighbor_id, edge_distance in graph.get(current_id, {}).items():
            next_distance = current_distance + edge_distance
            if next_distance >= distances.get(neighbor_id, float("inf")):
                continue
            distances[neighbor_id] = next_distance
            previous[neighbor_id] = current_id
            heappush(queue, (next_distance, neighbor_id))

    if destination_id not in distances:
        return [origin_id, destination_id]

    ordered = [destination_id]
    current = destination_id
    while current != origin_id:
        current = previous[current]
        ordered.append(current)
    ordered.reverse()
    return ordered


def shortest_distance_km(
    intersections: list[Intersection],
    origin_id: int,
    destination_id: int,
) -> float | None:
    path = shortest_path_ids(intersections, origin_id, destination_id)
    if not path:
        return None
    if len(path) == 1:
        return 0.0

    graph = _build_graph(intersections)
    total_distance = 0.0
    for first_id, second_id in zip(path, path[1:]):
        edge_distance = graph.get(first_id, {}).get(second_id)
        if edge_distance is None:
            return None
        total_distance += edge_distance
    return round(total_distance, 1)


def shortest_path(
    intersections: list[Intersection],
    origin_id: int,
    destination_id: int,
) -> list[Intersection]:
    lookup = {intersection.id: intersection for intersection in intersections}
    ordered_ids = shortest_path_ids(intersections, origin_id, destination_id)
    return [lookup[intersection_id] for intersection_id in ordered_ids if intersection_id in lookup]
