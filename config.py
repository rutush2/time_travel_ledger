import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR/ "ledger.db")

SNAPSHOT_INTERVAL_EVENTS: int = 50

HASH_ALGORITHM: str = "sha256"
GENESIS_PREV_HASH: str = "0" * 64

HOST: str = "127.0.0.1"
PORT: int = 8000

