from app.db.models import Intersection


def calculate_density_score(intersection: Intersection) -> float:
    theoretical_capacity = max(intersection.lane_count * 18, 1)
    occupancy_ratio = intersection.live_vehicle_count / theoretical_capacity
    width_modifier = max(0.75, min(intersection.road_width_m / 10.0, 1.35))
    congestion_bias = 0.65 + (intersection.historical_congestion * 0.35)
    density_score = occupancy_ratio * congestion_bias / width_modifier
    return round(density_score, 2)


def get_density_status(density_score: float) -> str:
    if density_score >= 1.25:
        return "High"
    if density_score >= 0.8:
        return "Moderate"
    return "Stable"
