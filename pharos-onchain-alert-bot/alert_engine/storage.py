from __future__ import annotations

import sqlite3
from pathlib import Path


class Storage:
    def __init__(self, path: str = "alert_bot.sqlite3") -> None:
        self.connection = sqlite3.connect(Path(path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (name TEXT PRIMARY KEY, block_number INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS seen_alerts (event_id TEXT NOT NULL, rule_name TEXT NOT NULL, PRIMARY KEY(event_id, rule_name));
            CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, rule_name TEXT, status TEXT, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """
        )
        self.connection.commit()

    def get_checkpoint(self, name: str, default: int = 0) -> int:
        row = self.connection.execute("SELECT block_number FROM checkpoints WHERE name = ?", (name,)).fetchone()
        return int(row[0]) if row else default

    def set_checkpoint(self, name: str, block_number: int) -> None:
        self.connection.execute("INSERT OR REPLACE INTO checkpoints(name, block_number) VALUES (?, ?)", (name, block_number))
        self.connection.commit()

    def claim_alert(self, event_id: str, rule_name: str) -> bool:
        try:
            self.connection.execute("INSERT INTO seen_alerts(event_id, rule_name) VALUES (?, ?)", (event_id, rule_name))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def record_notification(self, event_id: str, rule_name: str, status: str, detail: str = "") -> None:
        self.connection.execute("INSERT INTO notifications(event_id, rule_name, status, detail) VALUES (?, ?, ?, ?)", (event_id, rule_name, status, detail))
        self.connection.commit()

    def recent_notifications(self, limit: int = 20) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)))