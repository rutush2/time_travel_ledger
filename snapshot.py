import json
from typing import Any, Dict, Optional

from schema import Snapshot
from storage import get_connection


class SnapshotManager:

    def save_snapshot(
        self,
        aggregate_type: str,
        aggregate_id: str,
        last_sequence_id: int,
        state_payload: Dict[str, Any]
    ) -> Snapshot:

        canonical_state = json.dumps(state_payload, sort_keys=True)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO snapshots (
                    aggregate_type, aggregate_id, last_sequence_id, state_payload, created_at, is_valid
                ) VALUES (?, ?, ?, ?, datetime('now'), 1)
            """, (aggregate_type, aggregate_id, last_sequence_id, canonical_state))

            snapshot_id = cursor.lastrowid
            conn.commit()

            return Snapshot(
                snapshot_id=snapshot_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                last_sequence_id=last_sequence_id,
                state_payload=state_payload,
                is_valid=True
            )

    def get_latest_valid_snapshot(
        self,
        aggregate_type: str,
        aggregate_id: str,
        max_sequence_id: Optional[int] = None
    ) -> Optional[Snapshot]:

        with get_connection() as conn:
            cursor = conn.cursor()

            if max_sequence_id is not None:
                query = """
                    SELECT snapshot_id, aggregate_type, aggregate_id, last_sequence_id, 
                           state_payload, created_at, is_valid
                    FROM snapshots
                    WHERE aggregate_type = ? AND aggregate_id = ? 
                      AND is_valid = 1 AND last_sequence_id <= ?
                    ORDER BY last_sequence_id DESC
                    LIMIT 1
                """
                params = (aggregate_type, aggregate_id, max_sequence_id)
            else:
                query = """
                    SELECT snapshot_id, aggregate_type, aggregate_id, last_sequence_id, 
                           state_payload, created_at, is_valid
                    FROM snapshots
                    WHERE aggregate_type = ? AND aggregate_id = ? AND is_valid = 1
                    ORDER BY last_sequence_id DESC
                    LIMIT 1
                """
                params = (aggregate_type, aggregate_id)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row:
                return None

            return Snapshot(
                snapshot_id=row["snapshot_id"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                last_sequence_id=row["last_sequence_id"],
                state_payload=json.loads(row["state_payload"]),
                created_at=row["created_at"],
                is_valid=bool(row["is_valid"])
            )

    def invalidate_snapshots_from_sequence(
        self,
        aggregate_type: str,
        aggregate_id: str,
        from_sequence_id: int
    ) -> int:

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE snapshots
                SET is_valid = 0
                WHERE aggregate_type = ? AND aggregate_id = ? AND last_sequence_id >= ?
            """, (aggregate_type, aggregate_id, from_sequence_id))

            affected_count = cursor.rowcount
            conn.commit()
            return affected_count