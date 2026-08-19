import sqlite3
from typing import Dict, Any
import json
import config
from storage import get_connection


class TamperSimulator:

    def tamper_event_payload(self, sequence_id: int, corrupted_payload: Dict[str, Any]) -> bool:
        canonical_payload = json.dumps(corrupted_payload, sort_keys=True)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE events
                SET payload = ?
                WHERE sequence_id = ?
            """, (canonical_payload, sequence_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0