from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.db.models import EmergencyRoute


def activate_emergency_route(
    db: Session, severity_level: int, source: str, route_intersections: List[int]
) -> EmergencyRoute:
    route = EmergencyRoute(
        severity_level=severity_level,
        source=source,
        route_intersections=route_intersections,
        active=True,
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


def get_active_routes(db: Session) -> List[EmergencyRoute]:
    return db.query(EmergencyRoute).filter(EmergencyRoute.active.is_(True)).all()


def clear_route(db: Session, route_id: int) -> EmergencyRoute:
    route = db.query(EmergencyRoute).filter(EmergencyRoute.id == route_id).first()
    if route:
        route.active = False
        db.commit()
        db.refresh(route)
    return route


def is_emergency_active(db: Session) -> bool:
    return db.query(EmergencyRoute).filter(EmergencyRoute.active.is_(True)).count() > 0


def compute_emergency_corridor(
    route_intersections: List[int], start_time: datetime, window_seconds: int = 180
) -> List[dict]:
    corridor = []
    slot = start_time
    for intersection_id in route_intersections:
        corridor.append(
            {
                "intersection_id": intersection_id,
                "green_from": slot,
                "green_to": slot + timedelta(seconds=window_seconds),
            }
        )
        slot = slot + timedelta(seconds=window_seconds)
    return corridor
