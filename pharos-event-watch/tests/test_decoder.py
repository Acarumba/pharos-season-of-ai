from monitor.decoder import TRANSFER_TOPIC, decode_transfer_log, event_signature_topic


def word(value: int) -> str:
    return f"0x{value:064x}"


def test_transfer_topic_uses_keccak() -> None:
    assert event_signature_topic("Transfer(address,address,uint256)") == TRANSFER_TOPIC
    assert TRANSFER_TOPIC == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def test_decodes_indexed_addresses_and_amount() -> None:
    event = decode_transfer_log({
        "topics": [TRANSFER_TOPIC, word(0x11), word(0x22)],
        "data": word(1234567),
        "transactionHash": "0x" + "ab" * 32,
        "blockNumber": "0x10",
        "logIndex": "0x2",
    }, decimals=6, timestamp=1700000000)
    assert event.sender == "0x" + "00" * 19 + "11"
    assert event.recipient == "0x" + "00" * 19 + "22"
    assert event.raw_amount == 1234567
    assert event.amount == "1.234567"
    assert event.block_number == 16
    assert event.timestamp == 1700000000


def test_malformed_log_is_rejected() -> None:
    try:
        decode_transfer_log({"topics": []})
    except ValueError as exc:
        assert "three topics" in str(exc)
    else:
        raise AssertionError("malformed log was accepted")