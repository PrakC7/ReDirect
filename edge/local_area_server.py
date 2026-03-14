from dataclasses import asdict, dataclass, field
from datetime import datetime

from edge.edge_processor import (
    AreaSmallServerState,
    CameraFlowReading,
    CameraTargetOption,
    build_optimizer_upload_from_area_snapshot,
    create_area_small_server_state,
    snapshot_from_area_small_server_state,
    update_area_small_server_state,
)


@dataclass(slots=True)
class CameraInputReference:
    area_id: str
    camera_id: str
    controlled_intersection_id: int
    captured_at: datetime
    recording_reference: str
    recording_store: str = "preinstalled-local-camera-server"


@dataclass(slots=True)
class CameraCountResult:
    direction: str
    vehicle_count: int
    average_speed_kph: float | None = None
    emergency_detected: bool = False
    wrong_way_count: int = 0
    target_options: list[CameraTargetOption] = field(default_factory=list)


@dataclass(slots=True)
class ProcessedTelemetryRecord:
    recording_reference: str
    recording_store: str
    reading: CameraFlowReading


@dataclass(slots=True)
class LocalAreaOptimizerUpload:
    area_id: str
    controlled_intersection_id: int
    sequence_id: int
    local_snapshot: dict[str, object]
    optimizer_packet: dict[str, int]
    pending_processed_record_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class LocalAreaServer:
    area_id: str
    controlled_intersection_id: int
    window_minutes: int = 5
    priority_radius_km: float = 20.0
    pending_processed_records: list[ProcessedTelemetryRecord] = field(
        default_factory=list
    )
    _state: AreaSmallServerState = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._reset_state()

    def _reset_state(self, generated_at: datetime | None = None) -> None:
        self._state = create_area_small_server_state(
            area_id=self.area_id,
            controlled_intersection_id=self.controlled_intersection_id,
            generated_at=generated_at,
            window_minutes=self.window_minutes,
            priority_radius_km=self.priority_radius_km,
        )

    def _validate_camera_input(self, camera_input: CameraInputReference) -> None:
        if camera_input.area_id != self.area_id:
            raise ValueError("camera input area does not match the local server area")
        if camera_input.controlled_intersection_id != self.controlled_intersection_id:
            raise ValueError(
                "camera input intersection does not match the local server intersection"
            )
        if not camera_input.recording_reference.strip():
            raise ValueError("camera input must include a recording reference")

    def register_camera_input(
        self,
        camera_input: CameraInputReference,
    ) -> dict[str, object]:
        self._validate_camera_input(camera_input)
        return {
            "area_id": camera_input.area_id,
            "camera_id": camera_input.camera_id,
            "controlled_intersection_id": camera_input.controlled_intersection_id,
            "captured_at": camera_input.captured_at.isoformat(),
            "recording_reference": camera_input.recording_reference,
            "recording_store": camera_input.recording_store,
            "storage_managed_externally": True,
        }

    def add_count_result(
        self,
        camera_input: CameraInputReference,
        count_result: CameraCountResult,
    ) -> ProcessedTelemetryRecord:
        self.register_camera_input(camera_input)
        if count_result.vehicle_count < 0:
            raise ValueError("vehicle_count must be zero or greater")

        record = ProcessedTelemetryRecord(
            recording_reference=camera_input.recording_reference,
            recording_store=camera_input.recording_store,
            reading=CameraFlowReading(
                area_id=camera_input.area_id,
                camera_id=camera_input.camera_id,
                controlled_intersection_id=camera_input.controlled_intersection_id,
                captured_at=camera_input.captured_at,
                direction=count_result.direction,
                vehicle_count=count_result.vehicle_count,
                average_speed_kph=count_result.average_speed_kph,
                emergency_detected=count_result.emergency_detected,
                wrong_way_count=count_result.wrong_way_count,
                target_options=count_result.target_options,
            ),
        )
        self.pending_processed_records.append(record)
        update_area_small_server_state(self._state, record.reading)
        return record

    def build_upload(
        self,
        sequence_id: int,
        occupancy_index: float | None = None,
    ) -> LocalAreaOptimizerUpload:
        local_snapshot = snapshot_from_area_small_server_state(self._state)
        optimizer_packet = build_optimizer_upload_from_area_snapshot(
            local_snapshot,
            sequence_id,
            occupancy_index,
        )
        return LocalAreaOptimizerUpload(
            area_id=self.area_id,
            controlled_intersection_id=self.controlled_intersection_id,
            sequence_id=sequence_id,
            local_snapshot=local_snapshot,
            optimizer_packet=optimizer_packet,
            pending_processed_record_count=len(self.pending_processed_records),
        )

    def acknowledge_send(
        self,
        sequence_id: int,
        sent_at: datetime | None = None,
    ) -> dict[str, object]:
        cleared_record_count = len(self.pending_processed_records)
        self.pending_processed_records.clear()
        self._reset_state(generated_at=sent_at or datetime.utcnow())
        return {
            "sequence_id": sequence_id,
            "status": "Main server send acknowledged; transient model summaries cleared.",
            "cleared_processed_records": cleared_record_count,
            "raw_recordings_deleted": 0,
            "raw_recordings_managed_externally": True,
        }

