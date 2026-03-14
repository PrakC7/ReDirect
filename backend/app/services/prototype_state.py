from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


def _default_state() -> dict[str, Any]:
    return {
        "telemetry": {},
        "emergency_requests": [],
        "wrong_way_alerts": [],
    }


class PrototypeStateStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self._path = file_path or (
            Path(__file__).resolve().parents[2] / "runtime" / "prototype_state.json"
        )
        self._lock = Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(json.dumps(_default_state(), indent=2), encoding="utf-8")

    def _load_locked(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = _default_state()

        state = _default_state()
        state.update(raw)
        return state

    def _save_locked(self, state: dict[str, Any]) -> None:
        self._path.write_text(
            json.dumps(state, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load_emergency_requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._load_locked().get("emergency_requests", []))

    def save_emergency_requests(self, records: list[dict[str, Any]]) -> None:
        with self._lock:
            state = self._load_locked()
            state["emergency_requests"] = records
            self._save_locked(state)

    def load_telemetry(self) -> dict[int, dict[str, Any]]:
        with self._lock:
            payload = self._load_locked().get("telemetry", {})
            return {
                int(intersection_id): reading
                for intersection_id, reading in payload.items()
            }

    def upsert_telemetry(self, intersection_id: int, reading: dict[str, Any]) -> None:
        with self._lock:
            state = self._load_locked()
            telemetry = state.setdefault("telemetry", {})
            telemetry[str(intersection_id)] = reading
            self._save_locked(state)

    def load_wrong_way_alerts(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._load_locked().get("wrong_way_alerts", []))

    def save_wrong_way_alerts(self, alerts: list[dict[str, Any]]) -> None:
        with self._lock:
            state = self._load_locked()
            state["wrong_way_alerts"] = alerts
            self._save_locked(state)
