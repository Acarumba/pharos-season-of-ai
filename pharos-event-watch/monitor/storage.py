from __future__ import annotations

import sqlite3
from pathlib import Path
from .decoder import TransferEvent


class EventStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
            event_key TEXT PRIMARY KEY, transaction_hash TEXT NOT NULL, block_number INTEGER NOT NULL,
            log_index INTEGER NOT NULL, sender TEXT NOT NULL, recipient TEXT NOT NULL,
            raw_amount TEXT NOT NULL, amount TEXT NOT NULL, timestamp INTEGER
        );
        """)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def get_cursor(self) -> int | None:
        row = self.connection.execute("SELECT value FROM metadata WHERE key='cursor'").fetchone()
        return int(row[0]) if row else None

    def set_cursor(self, block: int) -> None:
        self.connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('cursor',?)", (str(block),))
        self.connection.commit()

    def add_event(self, event: TransferEvent) -> bool:
        cursor = self.connection.execute("""INSERT OR IGNORE INTO events
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (event.event_key, event.transaction_hash,
            event.block_number, event.log_index, event.sender, event.recipient, str(event.raw_amount),
            event.amount, event.timestamp))
        self.connection.commit()
        return cursor.rowcount == 1

    def events(self, limit: int = 100) -> list[dict]:
        rows = self.connection.execute("SELECT * FROM events ORDER BY block_number DESC, log_index DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
