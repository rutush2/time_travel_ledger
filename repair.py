import json
from typing import Dict, Any, Tuple
import config
from schema import calculate_event_hash
from storage import get_connection
from snapshot import SnapshotManager


class LedgerRepairEngine:

    def __init__(self):
        self.snapshot_manager = SnapshotManager()

    def repair_chain_from_sequence(self, start_sequence_id: int) -> Tuple[int, int]:

        with get_connection() as conn:
            cursor = conn.cursor()

            if start_sequence_id > 1:
                cursor.execute("SELECT hash FROM events WHERE sequence_id = ?", (start_sequence_id - 1,))
                prev_row = cursor.fetchone()
                if not prev_row:
                    raise ValueError(f"Preceding sequence ID {start_sequence_id - 1} does not exist.")
                running_prev_hash = prev_row["hash"]
            else:
                running_prev_hash = config.GENESIS_PREV_HASH

            cursor.execute("""
                SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload
                FROM events
                WHERE sequence_id >= ?
                ORDER BY sequence_id ASC
            """, (start_sequence_id,))
            events_to_repair = cursor.fetchall()

            resealed_count = 0
            affected_aggregates = set()

            for row in events_to_repair:
                seq_id = row["sequence_id"]
                timestamp = row["timestamp"]
                agg_type = row["aggregate_type"]
                agg_id = row["aggregate_id"]
                event_type = row["event_type"]
                payload = json.loads(row["payload"])

                new_hash = calculate_event_hash(
                    sequence_id=seq_id,
                    timestamp=timestamp,
                    aggregate_type=agg_type,
                    aggregate_id=agg_id,
                    event_type=event_type,
                    payload=payload,
                    prev_hash=running_prev_hash
                )

                cursor.execute("""
                    UPDATE events
                    SET prev_hash = ?, hash = ?
                    WHERE sequence_id = ?
                """, (running_prev_hash, new_hash, seq_id))

                running_prev_hash = new_hash
                resealed_count += 1
                affected_aggregates.add((agg_type, agg_id))

            conn.commit()

        snapshots_invalidated = 0
        for agg_type, agg_id in affected_aggregates:
            count = self.snapshot_manager.invalidate_snapshots_from_sequence(agg_type, agg_id, start_sequence_id)
            snapshots_invalidated += count

        return resealed_count, snapshots_invalidated