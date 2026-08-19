
---

### `README.md`

```markdown
# ⏳ time_travel_ledger

An event-sourced, append-only state engine built in Python. Features microsecond-precision state reconstruction, snapshot acceleration, retroactive timeline divergence calculation, and cryptographic SHA-256 chain verification with forensic repair capabilities.

---

## 🏛️ System Architecture

The engine uses deterministic event sourcing to separate mutation history from state projection:

```text
[ Incoming Mutation ]
          │
          ▼
┌───────────────────┐    SHA-256 Chain    ┌───────────────────┐
│   EventStore      │ ──────────────────► │  SQLite Database  │
│ (Append-Only Log) │                     │    (ledger.db)    │
└───────────────────┘                     └───────────────────┘
          │                                         │
          ├─── Periodic Threshold Check             │ Stream Replay
          ▼                                         ▼
┌───────────────────┐                     ┌───────────────────┐
│ SnapshotManager   │ ──────────────────► │    projection     │
│  (State Baselines)│                     │  (Pure State Engine)│
└───────────────────┘                     └───────────────────┘
                                                    │
                                                    ▼
                                          ┌───────────────────┐
                                          │   Reconstructed   │
                                          │    System State   │
                                          └───────────────────┘

```

---

## 🚀 Features

* **Immutable Event Sourcing**: Append-only log with SHA-256 cryptographic chain validation.
* **Deterministic Replay & Time Travel**: Reconstruct state at any sequence ID using snapshot acceleration + stream replay.
* **Retroactive Timeline Branching**: Ingest historical events, invalidate downstream snapshots, and evaluate head state divergence.
* **Forensic Audit & Chain Repair**: Detect exact sequence IDs where payload or link tampering occurred, with automated re-sealing.
* **Command & Control Dashboard**: Streamlit interface with interactive timeline scrubbers and Plotly sequence analytics.

---

## 🛠️ Project Structure

```text
time_travel_ledger/
├── config.py           # Core settings (database path, snapshot thresholds)
├── schema.py           # Pydantic models & SHA-256 canonical hashing
├── storage.py          # SQLite database connection manager
├── event_store.py      # Immutable event persistence & integrity checks
├── snapshot.py         # Snapshot generation & sequence invalidation
├── projection.py       # Pure state transformation logic
├── ledger_engine.py    # System orchestrator
├── auditor.py          # Forensic chain scanner
├── temper.py           # Database tamper simulator
├── repair.py           # Cryptographic chain re-sealing engine
├── server.py           # FastAPI REST endpoints
└── dashboard.py        # Streamlit C2 UI

```

---

## ⚡ Quickstart

### 1. Install Dependencies

```bash
pip install fastapi uvicorn pydantic requests streamlit pandas plotly

```

### 2. Start API Server

```bash
python server.py

```

* Server runs at `http://127.0.0.1:8000`
* Interactive API docs at `http://127.0.0.1:8000/docs`

### 3. Start C2 Control Dashboard

Open a second terminal window:

```bash
streamlit run dashboard.py

```

* Access the dashboard at `http://localhost:8501`

```

---

