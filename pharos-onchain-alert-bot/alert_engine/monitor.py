from __future__ import annotations

from dataclasses import dataclass

from .decoder import TRANSFER_TOPIC, TransferEvent, decode_transfer_log
from .mcp_client import PharosMCPClient
from .rules import AlertRule
from .storage import Storage


@dataclass
class Alert:
    event: TransferEvent
    rule: AlertRule


class Monitor:
    def __init__(self, client: PharosMCPClient, storage: Storage, token: str, rules: list[AlertRule], start_block: int | None = None, enabled_event_types: set[str] | None = None) -> None:
        self.client, self.storage, self.token, self.rules = client, storage, token.lower(), rules
        self.enabled_event_types = enabled_event_types if enabled_event_types is not None else {"transfer"}
        self.decimals = client.token_decimals(token)
        self.checkpoint = storage.get_checkpoint("transfer", start_block or 0)

    def poll_once(self) -> list[Alert]:
        if "transfer" not in self.enabled_event_types:
            return []
        latest = self.client.block_number()
        if latest <= self.checkpoint:
            return []
        logs = self.client.logs(self.token, TRANSFER_TOPIC, self.checkpoint + 1, latest)
        alerts: list[Alert] = []
        for log in logs:
            event = decode_transfer_log(log, token_decimals=self.decimals)
            for rule in self.rules:
                if rule.matches(event) and self.storage.claim_alert(event.event_id, rule.name):
                    alerts.append(Alert(event, rule))
        self.checkpoint = latest
        self.storage.set_checkpoint("transfer", latest)
        return alerts