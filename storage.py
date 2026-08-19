import sqlite3
from typing import Generator
import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_aggregate 
            ON events (aggregate_type, aggregate_id, sequence_id);
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                last_sequence_id INTEGER NOT NULL,
                state_payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_valid INTEGER NOT NULL DEFAULT 1
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_lookup 
            ON snapshots (aggregate_type, aggregate_id, last_sequence_id, is_valid);
        """)

        conn.commit()