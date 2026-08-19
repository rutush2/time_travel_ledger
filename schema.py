import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


def calculate_event_hash(
        sequence_id: int,
        timestamp: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        prev_hash: str
) -> str:
    canonical_payload = json.dumps(payload, sort_keys=True)

    hash_payload = (
        f"{sequence_id}|{timestamp}|{aggregate_type}|"
        f"{aggregate_id}|{event_type}|{canonical_payload}|{prev_hash}"
    )
    return hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()


class EventEnvelope(BaseModel):
    sequence_id: int = Field(..., description="Monotonically increasing sequence identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of event recording"
    )
    aggregate_type: str = Field(..., description="Domain entity classification (e.g., account, directory)")
    aggregate_id: str = Field(..., description="Unique identifier of the target domain entity")
    event_type: str = Field(..., description="Specific event action (e.g., DEPOSIT, WITHDRAW, TRANSFER)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event mutation metadata")
    prev_hash: str = Field(..., description="Cryptographic SHA-256 hash of the preceding event")
    hash: str = Field(..., description="SHA-256 hash of the current event envelope")

    def verify_hash(self) -> bool:
        expected_hash = calculate_event_hash(
            sequence_id=self.sequence_id,
            timestamp=self.timestamp,
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            event_type=self.event_type,
            payload=self.payload,
            prev_hash=self.prev_hash
        )
        return self.hash == expected_hash


class Snapshot(BaseModel):
    snapshot_id: Optional[int] = Field(None, description="Primary key of the snapshot record")
    aggregate_type: str = Field(..., description="Domain entity classification")
    aggregate_id: str = Field(..., description="Unique identifier of the target domain entity")
    last_sequence_id: int = Field(..., description="Highest sequence ID included in this snapshot state")
    state_payload: Dict[str, Any] = Field(..., description="Full state dictionary at last_sequence_id")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of snapshot creation"
    )
    is_valid: bool = Field(True, description="Flag indicating if retroactive injections invalidated this baseline")


class LedgerState(BaseModel):
    aggregate_type: str
    aggregate_id: str
    sequence_id: int
    timestamp: str
    state: Dict[str, Any]
    events_replayed: int