from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from uuid import uuid4

from app.db.models import Intersection
from app.schemas import (
    ActiveEmergencySummary,
    CorridorStep,
    EmergencyRequestCreate,
    EmergencyRequestRecord,
    IntersectionPriorityStep,
)

PRIORITY_TO_TIME_SAVED = {"Critical": 8, "High": 5, "Medium": 3}
PRIORITY_TO_WINDOW_SECONDS = {"Critical": 45, "High": 60, "Medium": 75}
PRIORITY_TO_SEVERITY = {"Critical": 3, "High": 2, "Medium": 1}


def build_corridor(
    intersections: list[Intersection],
    priority: str,
    start_time: datetime | None = None,
    intersection_priorities: dict[int, IntersectionPriorityStep] | None = None,
) -> list[CorridorStep]:
    slot = start_time or datetime.utcnow()
    window_seconds = PRIORITY_TO_WINDOW_SECONDS[priority]
    corridor: list[CorridorStep] = []

    for intersection in intersections:
        priority_step = (
            intersection_priorities.get(intersection.id)
            if intersection_priorities
            else None
        )
        corridor.append(
            CorridorStep(
                intersection_id=intersection.id,
                intersection_name=intersection.name,
                green_from=slot,
                green_to=slot + timedelta(seconds=window_seconds),
                distance_km=priority_step.distance_km if priority_step else None,
                priority_phase=priority_step.priority_phase if priority_step else None,
                target_flow_direction=(
                    priority_step.target_flow_direction if priority_step else None
                ),
                approaching_zone=(
                    priority_step.approaching_zone if priority_step else None
                ),
                approaching_vehicle_share=(
                    priority_step.approaching_vehicle_share if priority_step else None
                ),
                movement_alignment=(
                    priority_step.movement_alignment if priority_step else None
                ),
            )
        )
        slot += timedelta(seconds=window_seconds)

    return corridor


class EmergencyRequestStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._records: list[EmergencyRequestRecord] = []
        self._lock = Lock()

    def create(
        self,
        payload: EmergencyRequestCreate,
        corridor: list[CorridorStep],
        priority_radius_km: int,
        priority_intersections: list[IntersectionPriorityStep],
    ) -> EmergencyRequestRecord:
        submitted_at = datetime.utcnow()
        window_seconds = PRIORITY_TO_WINDOW_SECONDS[payload.priority]
        record = EmergencyRequestRecord(
            request_id=f"RD-{uuid4().hex[:8].upper()}",
            status="Corridor scheduled",
            submitted_at=submitted_at,
            suggested_time_saved_minutes=PRIORITY_TO_TIME_SAVED[payload.priority],
            corridor_window_seconds=window_seconds,
            priority_radius_km=priority_radius_km,
            corridor=corridor,
            priority_intersections=priority_intersections,
            **payload.model_dump(),
        )

        with self._lock:
            self._prune_locked(submitted_at)
            self._records.append(record)

        return record

    def list_active(self) -> list[EmergencyRequestRecord]:
        with self._lock:
            now = datetime.utcnow()
            self._prune_locked(now)
            return sorted(
                self._records,
                key=lambda record: (
                    -PRIORITY_TO_SEVERITY[record.priority],
                    record.submitted_at,
                ),
            )

    def list_active_summaries(self) -> list[ActiveEmergencySummary]:
        return [
            ActiveEmergencySummary(
                request_id=record.request_id,
                vehicle_type=record.vehicle_type,
                priority=record.priority,
                origin=record.origin,
                destination=record.destination,
                submitted_at=record.submitted_at,
                suggested_time_saved_minutes=record.suggested_time_saved_minutes,
            )
            for record in self.list_active()
        ]

    def _prune_locked(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self._ttl_seconds)
        self._records = [
            record for record in self._records if record.submitted_at >= cutoff
        ]
