import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

import config
from schema import calculate_event_hash
from storage import get_connection


class AuditViolation(BaseModel):
    sequence_id: int
    aggregate_type: str
    aggregate_id: str
    timestamp: str
    violation_type: str
    recorded_hash: str
    calculated_hash: str
    recorded_prev_hash: str
    expected_prev_hash: str


class ForensicAuditReport(BaseModel):
    total_events_scanned: int
    is_chain_valid: bool
    first_corrupted_sequence_id: Optional[int] = None
    violations_found: List[AuditViolation] = []
    affected_aggregates: List[str] = []


class LedgerAuditor:

    def perform_full_audit(self) -> ForensicAuditReport:

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sequence_id, timestamp, aggregate_type, aggregate_id, event_type, payload, prev_hash, hash
                FROM events
                ORDER BY sequence_id ASC
            """)
            rows = cursor.fetchall()

        total_events = len(rows)
        violations: List[AuditViolation] = []
        affected_aggregates_set = set()
        expected_prev_hash = config.GENESIS_PREV_HASH
        expected_seq_id = 1
        first_corrupted_seq: Optional[int] = None

        for row in rows:
            seq_id = row["sequence_id"]
            timestamp = row["timestamp"]
            agg_type = row["aggregate_type"]
            agg_id = row["aggregate_id"]
            event_type = row["event_type"]
            payload = json.loads(row["payload"])
            rec_prev_hash = row["prev_hash"]
            rec_hash = row["hash"]

            calc_hash = calculate_event_hash(
                sequence_id=seq_id,
                timestamp=timestamp,
                aggregate_type=agg_type,
                aggregate_id=agg_id,
                event_type=event_type,
                payload=payload,
                prev_hash=rec_prev_hash
            )

            if seq_id != expected_seq_id:
                violations.append(AuditViolation(
                    sequence_id=seq_id,
                    aggregate_type=agg_type,
                    aggregate_id=agg_id,
                    timestamp=timestamp,
                    violation_type="SEQUENCE_GAP",
                    recorded_hash=rec_hash,
                    calculated_hash=calc_hash,
                    recorded_prev_hash=rec_prev_hash,
                    expected_prev_hash=expected_prev_hash
                ))
                if first_corrupted_seq is None:
                    first_corrupted_seq = seq_id
                affected_aggregates_set.add(f"{agg_type}:{agg_id}")

            if rec_prev_hash != expected_prev_hash:
                violations.append(AuditViolation(
                    sequence_id=seq_id,
                    aggregate_type=agg_type,
                    aggregate_id=agg_id,
                    timestamp=timestamp,
                    violation_type="PREV_HASH_MISMATCH",
                    recorded_hash=rec_hash,
                    calculated_hash=calc_hash,
                    recorded_prev_hash=rec_prev_hash,
                    expected_prev_hash=expected_prev_hash
                ))
                if first_corrupted_seq is None:
                    first_corrupted_seq = seq_id
                affected_aggregates_set.add(f"{agg_type}:{agg_id}")

            if rec_hash != calc_hash:
                violations.append(AuditViolation(
                    sequence_id=seq_id,
                    aggregate_type=agg_type,
                    aggregate_id=agg_id,
                    timestamp=timestamp,
                    violation_type="HASH_MISMATCH",
                    recorded_hash=rec_hash,
                    calculated_hash=calc_hash,
                    recorded_prev_hash=rec_prev_hash,
                    expected_prev_hash=expected_prev_hash
                ))
                if first_corrupted_seq is None:
                    first_corrupted_seq = seq_id
                affected_aggregates_set.add(f"{agg_type}:{agg_id}")

            expected_prev_hash = rec_hash
            expected_seq_id = seq_id + 1

        is_valid = len(violations) == 0

        return ForensicAuditReport(
            total_events_scanned=total_events,
            is_chain_valid=is_valid,
            first_corrupted_sequence_id=first_corrupted_seq,
            violations_found=violations,
            affected_aggregates=list(affected_aggregates_set)
        )