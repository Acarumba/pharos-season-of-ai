from __future__ import annotations

import re
from dataclasses import dataclass

from .decoder import TransferEvent

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_address(value: str) -> str:
    if not ADDRESS_RE.fullmatch(value):
        raise ValueError("address must be a 20-byte 0x-prefixed hex value")
    return value.lower()


def validate_email(value: str) -> str:
    value = value.strip()
    if not EMAIL_RE.fullmatch(value):
        raise ValueError("email must be a valid recipient address")
    return value


def parse_threshold(value: str, decimals: int) -> int:
    try:
        text = str(value).strip()
        if not re.fullmatch(r"\d+(?:\.\d+)?", text):
            raise ValueError
        whole, _, fraction = text.partition(".")
        if len(fraction) > decimals:
            raise ValueError
        return int(whole) * 10**decimals + int((fraction + "0" * decimals)[:decimals] or 0)
    except (TypeError, ValueError):
        raise ValueError(f"threshold must be a non-negative number with at most {decimals} decimals") from None


@dataclass(frozen=True)
class AlertRule:
    name: str
    enabled: bool = True
    threshold_raw: int | None = None
    sender: str | None = None
    recipient: str | None = None
    monitored_address: str | None = None

    def matches(self, event: TransferEvent) -> bool:
        if not self.enabled:
            return False
        if self.threshold_raw is not None and event.amount_raw <= self.threshold_raw:
            return False
        if self.sender and event.sender != self.sender.lower():
            return False
        if self.recipient and event.recipient != self.recipient.lower():
            return False
        if self.monitored_address and self.monitored_address.lower() not in {event.sender, event.recipient}:
            return False
        return True