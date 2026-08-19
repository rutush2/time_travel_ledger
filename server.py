import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import config
from schema import EventEnvelope, LedgerState
from ledger_engine import LedgerEngine
from auditor import LedgerAuditor, ForensicAuditReport
from temper import TamperSimulator
from repair import LedgerRepairEngine

sys.path.insert(0, str(Path(__file__).resolve().parent))

app = FastAPI(
    title="Replay-Driven Audit & Time-Travel Ledger API",
    version="1.0.0",
    description="REST interface for immutable event appending, point-in-time state reconstruction, retroactive timeline branching, and forensic audit repair."
)

engine = LedgerEngine()
auditor = LedgerAuditor()
tamper_sim = TamperSimulator()
repair_engine = LedgerRepairEngine()


class RecordEventRequest(BaseModel):
    aggregate_type: str = Field(..., example="cluster_node")
    aggregate_id: str = Field(..., example="node-eu-west-04")
    event_type: str = Field(..., example="PROVISION_NODE")
    payload: Dict[str, Any] = Field(default_factory=dict, example={"hostname": "worker-04", "cpu_cores": 16})
    timestamp: Optional[str] = Field(None, example="2026-08-18T10:00:00Z")


class InjectRetroactiveRequest(BaseModel):
    aggregate_type: str = Field(..., example="cluster_node")
    aggregate_id: str = Field(..., example="node-eu-west-04")
    retroactive_timestamp: str = Field(..., example="2026-08-16T12:00:00Z")
    event_type: str = Field(..., example="ISOLATE_SUBNET")
    payload: Dict[str, Any] = Field(default_factory=dict, example={"reason": "security_quarantine"})


class TamperRequest(BaseModel):
    sequence_id: int
    corrupted_payload: Dict[str, Any]


class RepairRequest(BaseModel):
    start_sequence_id: int


@app.post("/api/events", response_model=EventEnvelope, status_code=201)
def record_event(request: RecordEventRequest):
    try:
        event = engine.record_event(
            aggregate_type=request.aggregate_type,
            aggregate_id=request.aggregate_id,
            event_type=request.event_type,
            payload=request.payload,
            timestamp=request.timestamp
        )
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/{aggregate_type}/{aggregate_id}", response_model=LedgerState)
def get_state(
    aggregate_type: str,
    aggregate_id: str,
    at_sequence_id: Optional[int] = Query(None, description="Reconstruct state at exact sequence ID")
):
    try:
        if at_sequence_id is not None:
            return engine.get_state_at_sequence(aggregate_type, aggregate_id, at_sequence_id)
        return engine.get_current_state(aggregate_type, aggregate_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inject-retroactive")
def inject_retroactive_event(request: InjectRetroactiveRequest):
    try:
        injected_event, divergence_delta = engine.inject_retroactive_event(
            aggregate_type=request.aggregate_type,
            aggregate_id=request.aggregate_id,
            retroactive_timestamp=request.retroactive_timestamp,
            event_type=request.event_type,
            payload=request.payload
        )
        return {
            "status": "success",
            "injected_event": injected_event,
            "divergence_delta": divergence_delta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/integrity/check")
def check_ledger_integrity():
    try:
        is_valid = engine.event_store.verify_ledger_integrity()
        return {
            "integrity_valid": is_valid,
            "message": "Cryptographic hash chain intact" if is_valid else "CORRUPTED: SHA-256 chain verification failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forensics/audit", response_model=ForensicAuditReport)
def run_forensic_audit():
    return auditor.perform_full_audit()


@app.post("/api/forensics/simulate-tamper")
def simulate_tamper(request: TamperRequest):
    success = tamper_sim.tamper_event_payload(request.sequence_id, request.corrupted_payload)
    if not success:
        raise HTTPException(status_code=404, detail="Sequence ID not found")
    return {"status": "success", "message": f"Tampered event {request.sequence_id}"}


@app.post("/api/forensics/repair")
def repair_ledger_chain(request: RepairRequest):
    try:
        resealed, invalidated_snaps = repair_engine.repair_chain_from_sequence(request.start_sequence_id)
        return {
            "status": "success",
            "events_resealed": resealed,
            "snapshots_invalidated": invalidated_snaps
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=config.HOST, port=config.PORT, reload=True)