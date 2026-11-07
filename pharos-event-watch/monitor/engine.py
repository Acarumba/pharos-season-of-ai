from __future__ import annotations

import time
from dataclasses import dataclass, field
from .decoder import TRANSFER_TOPIC, TransferEvent, decode_transfer_log
from .storage import EventStore


@dataclass
class MonitorStats:
    last_success: float | None = None
    last_error: str | None = None
    successful_polls: int = 0
    duplicates: int = 0
    started_at: float | None = None
    next_poll: float = 0


@dataclass
class MonitorEngine:
    client: object
    store: EventStore
    contract: str
    decimals: int = 6
    poll_interval: float = 10
    cursor: int | None = None
    stats: MonitorStats = field(default_factory=MonitorStats)

    def start(self, start_block: int | None = None, resume: bool = True) -> None:
        if resume and self.store.get_cursor() is not None:
            self.cursor = self.store.get_cursor()
        elif start_block is not None:
            self.cursor = start_block - 1
        else:
            self.cursor = self.client.get_block_number()
        self.stats.started_at = self.stats.started_at or time.time()
        self.stats.next_poll = 0

    def poll_once(self, force: bool = False) -> list[TransferEvent]:
        if self.cursor is None:
            self.start()
        if not force and time.time() < self.stats.next_poll:
            return []
        try:
            latest = self.client.get_block_number()
            if latest <= self.cursor:
                self._success()
                return []
            discovered: list[TransferEvent] = []
            range_start = self.cursor + 1
            while range_start <= latest:
                range_end = min(range_start + 999, latest)
                logs = self.client.get_logs(self.contract, TRANSFER_TOPIC, range_start, range_end)
                timestamps: dict[int, int | None] = {}
                for log in logs:
                    block = _number(log.get("blockNumber"))
                    if block not in timestamps:
                        timestamps[block] = self.client.get_block_timestamp(block)
                    try:
                        event = decode_transfer_log(log, self.decimals, timestamps[block])
                    except (TypeError, ValueError):
                        continue
                    if self.store.add_event(event):
                        discovered.append(event)
                    else:
                        self.stats.duplicates += 1
                self.store.set_cursor(range_end)
                self.cursor = range_end
                range_start = range_end + 1
            self._success()
            return discovered
        except Exception as exc:
            self.stats.last_error = str(exc)
            self.stats.next_poll = time.time() + self.poll_interval
            raise

    def _success(self) -> None:
        self.stats.last_success = time.time()
        self.stats.last_error = None
        self.stats.successful_polls += 1
        self.stats.next_poll = time.time() + self.poll_interval


def _number(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    raise ValueError("log is missing a block number")
