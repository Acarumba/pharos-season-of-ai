from tempfile import TemporaryDirectory

from monitor.decoder import TRANSFER_TOPIC, decode_transfer_log
from monitor.storage import EventStore


def test_transaction_and_log_index_are_deduplication_key() -> None:
    log = {
        "topics": [TRANSFER_TOPIC, "0x" + "0" * 63 + "1", "0x" + "0" * 63 + "2"],
        "data": "0x64",
        "transactionHash": "0x" + "ab" * 32,
        "blockNumber": "0x10",
        "logIndex": "0x0",
    }
    event = decode_transfer_log(log)
    with TemporaryDirectory() as directory:
        store = EventStore(directory + "/events.sqlite3")
        try:
            assert store.add_event(event) is True
            assert store.add_event(event) is False
            assert store.count() == 1
        finally:
            store.close()
