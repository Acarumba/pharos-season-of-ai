from __future__ import annotations

from dataclasses import dataclass

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a3df523b3ef"


def _address(topic: str) -> str:
    value = topic.removeprefix("0x")
    if len(value) != 64:
        raise ValueError("indexed address topic must contain 32 bytes")
    return "0x" + value[-40:]


@dataclass(frozen=True)
class TransferEvent:
    token: str
    sender: str
    recipient: str
    amount_raw: int
    transaction_hash: str
    block_number: int
    log_index: int
    timestamp: int | None = None

    @property
    def event_id(self) -> str:
        return f"{self.transaction_hash}:{self.log_index}"


def decode_transfer_log(log: dict, *, token_decimals: int = 6, timestamp: int | None = None) -> TransferEvent:
    topics = log.get("topics", [])
    if len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC:
        raise ValueError("log is not an ERC-20 Transfer event")
    data = log.get("data", "0x").removeprefix("0x")
    if len(data) != 64:
        raise ValueError("Transfer data must contain one uint256 amount")
    return TransferEvent(
        token=str(log.get("address", "")).lower(),
        sender=_address(topics[1]).lower(),
        recipient=_address(topics[2]).lower(),
        amount_raw=int(data, 16),
        transaction_hash=str(log.get("transactionHash", "")),
        block_number=int(log["blockNumber"], 16) if isinstance(log["blockNumber"], str) else int(log["blockNumber"]),
        log_index=int(log.get("logIndex", 0), 16) if isinstance(log.get("logIndex", 0), str) else int(log.get("logIndex", 0)),
        timestamp=timestamp,
    )


def format_amount(amount_raw: int, decimals: int) -> str:
    whole, fraction = divmod(amount_raw, 10**decimals)
    if fraction == 0:
        return str(whole)
    return f"{whole}.{fraction:0{decimals}d}".rstrip("0")