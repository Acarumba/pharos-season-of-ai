from __future__ import annotations

from decimal import Decimal


def decode_uint256(result: str) -> int:
    if len(result) != 66 or not result.startswith("0x"):
        raise ValueError("expected a single uint256 ABI result")
    try:
        return int(result[2:], 16)
    except ValueError as exc:
        raise ValueError("uint256 result contains invalid hexadecimal") from exc


def decode_string(result: str) -> str:
    if not result.startswith("0x") or len(result) < 130 or (len(result) - 2) % 64:
        raise ValueError("expected an ABI-encoded string result")
    try:
        payload = bytes.fromhex(result[2:])
        if len(payload) < 64:
            raise ValueError("ABI string result is missing required words")

        offset = int.from_bytes(payload[:32], "big")
        if offset < 32 or offset % 32 or offset + 32 > len(payload):
            raise ValueError("malformed ABI string offset")

        length_word_end = offset + 32
        length = int.from_bytes(payload[offset:length_word_end], "big")
        data_end = length_word_end + length
        padded_end = length_word_end + ((length + 31) // 32) * 32
        if data_end > len(payload) or padded_end != len(payload):
            raise ValueError("malformed ABI string length or padding")
        if any(payload[data_end:padded_end]):
            raise ValueError("ABI string padding must be zero")

        end = data_end
        if end > len(payload):
            raise ValueError("malformed ABI string length")
        return payload[offset + 32 : end].decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("malformed ABI string result") from exc


def format_units(value: int, decimals: int) -> str:
    if value < 0:
        raise ValueError("value must be non-negative")
    if decimals < 0:
        raise ValueError("decimals must be non-negative")
    amount = Decimal(value).scaleb(-decimals)
    if decimals == 0:
        return str(value)
    return format(amount, "f").rstrip("0").rstrip(".")