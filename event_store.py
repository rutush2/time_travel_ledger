import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from schema import EventEnvelope, calculate_event_hash
from storage import get_connection


class EventStore:
    def get_latest_event(self) -> Optional[EventEnvelope]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload, prev_hash, hash
                FROM events
                ORDER BY sequence_id DESC
                LIMIT 1
            """)
            row = cursor.fetchone()

            if not row:
                return None

            return EventEnvelope(
                sequence_id=row["sequence_id"],
                timestamp=row["timestamp"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload"]),
                prev_hash=row["prev_hash"],
                hash=row["hash"]
            )

    def append_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> EventEnvelope:

        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()

            latest_event = self.get_latest_event()
            if latest_event:
                next_sequence_id = latest_event.sequence_id + 1
                prev_hash = latest_event.hash
            else:
                next_sequence_id = 1
                prev_hash = config.GENESIS_PREV_HASH

            current_hash = calculate_event_hash(
                sequence_id=next_sequence_id,
                timestamp=timestamp,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                prev_hash=prev_hash
            )

            canonical_payload = json.dumps(payload, sort_keys=True)

            cursor.execute("""
                INSERT INTO events (
                    sequence_id, timestamp, aggregate_type, aggregate_id, 
                    event_type, payload, prev_hash, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_sequence_id, timestamp, aggregate_type, aggregate_id,
                event_type, canonical_payload, prev_hash, current_hash
            ))

            conn.commit()

            return EventEnvelope(
                sequence_id=next_sequence_id,
                timestamp=timestamp,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                prev_hash=prev_hash,
                hash=current_hash
            )

    def fetch_events_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        from_sequence_id: int = 1,
        to_sequence_id: Optional[int] = None
    ) -> List[EventEnvelope]:

        with get_connection() as conn:
            cursor = conn.cursor()

            if to_sequence_id is not None:
                query = """
                    SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload, prev_hash, hash
                    FROM events
                    WHERE aggregate_type = ? AND aggregate_id = ?
                      AND sequence_id >= ? AND sequence_id <= ?
                    ORDER BY sequence_id ASC
                """
                params = (aggregate_type, aggregate_id, from_sequence_id, to_sequence_id)
            else:
                query = """
                    SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload, prev_hash, hash
                    FROM events
                    WHERE aggregate_type = ? AND aggregate_id = ?
                      AND sequence_id >= ?
                    ORDER BY sequence_id ASC
                """
                params = (aggregate_type, aggregate_id, from_sequence_id)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append(EventEnvelope(
                    sequence_id=row["sequence_id"],
                    timestamp=row["timestamp"],
                    aggregate_type=row["aggregate_type"],
                    aggregate_id=row["aggregate_id"],
                    event_type=row["event_type"],
                    payload=json.loads(row["payload"]),
                    prev_hash=row["prev_hash"],
                    hash=row["hash"]
                ))
            return events

    def verify_ledger_integrity(self) -> bool:

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload, prev_hash, hash
                FROM events
                ORDER BY sequence_id ASC
            """)
            rows = cursor.fetchall()

            expected_prev_hash = config.GENESIS_PREV_HASH

            for row in rows:
                payload = json.loads(row["payload"])
                calculated_hash = calculate_event_hash(
                    sequence_id=row["sequence_id"],
                    timestamp=row["timestamp"],
                    aggregate_type=row["aggregate_type"],
                    aggregate_id=row["aggregate_id"],
                    event_type=row["event_type"],
                    payload=payload,
                    prev_hash=row["prev_hash"]
                )

                if row["prev_hash"] != expected_prev_hash or row["hash"] != calculated_hash:
                    return False

                expected_prev_hash = row["hash"]

            return True