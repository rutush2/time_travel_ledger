from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

import config
from schema import EventEnvelope, LedgerState, Snapshot
from storage import init_db
from event_store import EventStore
from snapshot import SnapshotManager
from projection import project_state


class LedgerEngine:


    def __init__(self):
        init_db()
        self.event_store = EventStore()
        self.snapshot_manager = SnapshotManager()

    def record_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> EventEnvelope:

        event = self.event_store.append_event(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            timestamp=timestamp
        )

        self._check_and_create_snapshot(aggregate_type, aggregate_id, event.sequence_id)

        return event

    def _check_and_create_snapshot(
        self,
        aggregate_type: str,
        aggregate_id: str,
        current_sequence_id: int
    ) -> Optional[Snapshot]:

        latest_snapshot = self.snapshot_manager.get_latest_valid_snapshot(aggregate_type, aggregate_id)
        last_snap_seq = latest_snapshot.last_sequence_id if latest_snapshot else 0

        if (current_sequence_id - last_snap_seq) >= config.SNAPSHOT_INTERVAL_EVENTS:
            state_result = self.get_state_at_sequence(aggregate_type, aggregate_id, current_sequence_id)
            return self.snapshot_manager.save_snapshot(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                last_sequence_id=current_sequence_id,
                state_payload=state_result.state
            )
        return None

    def get_state_at_sequence(
        self,
        aggregate_type: str,
        aggregate_id: str,
        target_sequence_id: int
    ) -> LedgerState:

        snapshot = self.snapshot_manager.get_latest_valid_snapshot(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            max_sequence_id=target_sequence_id
        )

        if snapshot:
            base_state = snapshot.state_payload
            from_seq = snapshot.last_sequence_id + 1
        else:
            base_state = {}
            from_seq = 1

        events = self.event_store.fetch_events_for_aggregate(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            from_sequence_id=from_seq,
            to_sequence_id=target_sequence_id
        )

        projected_state = project_state(base_state, events)
        last_timestamp = events[-1].timestamp if events else (snapshot.created_at if snapshot else datetime.now(timezone.utc).isoformat())

        return LedgerState(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            sequence_id=target_sequence_id,
            timestamp=last_timestamp,
            state=projected_state,
            events_replayed=len(events)
        )

    def get_current_state(
        self,
        aggregate_type: str,
        aggregate_id: str
    ) -> LedgerState:

        latest_event = self.event_store.get_latest_event()
        if not latest_event:
            return LedgerState(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                sequence_id=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                state={},
                events_replayed=0
            )

        return self.get_state_at_sequence(aggregate_type, aggregate_id, latest_event.sequence_id)

    def inject_retroactive_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        retroactive_timestamp: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Tuple[EventEnvelope, Dict[str, Any]]:

        original_state_obj = self.get_current_state(aggregate_type, aggregate_id)

        injected_event = self.event_store.append_event(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            timestamp=retroactive_timestamp
        )

        self.snapshot_manager.invalidate_snapshots_from_sequence(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            from_sequence_id=injected_event.sequence_id
        )

        new_state_obj = self.get_current_state(aggregate_type, aggregate_id)

        divergence_delta = {
            "original_head_sequence": original_state_obj.sequence_id,
            "new_head_sequence": new_state_obj.sequence_id,
            "injected_at_sequence": injected_event.sequence_id,
            "original_state": original_state_obj.state,
            "recalculated_state": new_state_obj.state
        }

        return injected_event, divergence_delta