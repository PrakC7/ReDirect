from typing import Dict, List, Tuple

from app.core.config import settings
from app.db.models import Intersection


def calculate_priority_score(
    density_score: float,
    road_priority_weight: float,
    vehicle_distribution: Dict[str, int] = None,
) -> float:
    base_score = density_score * (1.0 + road_priority_weight)
    
    # Public Transport Priority:
    # Boost priority if buses are detected.
    # Each bus adds 15% to the priority score, up to a max of 50% boost.
    bus_boost = 0.0
    if vehicle_distribution:
        bus_count = vehicle_distribution.get("bus", 0)
        bus_boost = min(bus_count * 0.15, 0.5)
    
    return base_score * (1.0 + bus_boost)


def generate_green_time(priority_score: float, max_priority: float) -> int:
    if max_priority <= 0:
        return settings.signal_min_green
    ratio = priority_score / max_priority if max_priority > 0 else 0
    green_time = int(
        settings.signal_min_green
        + ratio * (settings.signal_max_green - settings.signal_min_green)
    )
    return max(settings.signal_min_green, min(settings.signal_max_green, green_time))


def build_signal_plan(
    intersections: List[Tuple[Intersection, float, Dict[str, int]]]
) -> List[Tuple[int, float, float, int]]:
    """
    Builds a signal plan for a list of intersections.
    Input: List of (Intersection, density_score, vehicle_distribution)
    Output: List of (intersection_id, density_score, priority_score, green_time)
    """
    priorities = []
    for intersection, density_score, distribution in intersections:
        priority = calculate_priority_score(
            density_score, intersection.road_priority_weight, distribution
        )
        priorities.append((intersection.id, density_score, priority))

    max_priority = max((p[2] for p in priorities), default=0.0)
    
    plan = []
    for intersection_id, density_score, priority_score in sorted(
        priorities, key=lambda item: item[2], reverse=True
    ):
        green_time = generate_green_time(priority_score, max_priority)
        plan.append((intersection_id, density_score, priority_score, green_time))
    return plan
