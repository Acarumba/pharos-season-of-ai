from tempfile import TemporaryDirectory

from monitor.engine import MonitorEngine
from monitor.storage import EventStore


class FakeClient:
    def __init__(self) -> None:
        self.latest = 10
        self.log_calls: list[tuple[int, int]] = []
        self.fail_logs = False

    def get_block_number(self) -> int:
        return self.latest

    def get_logs(self, address: str, topic: str, start: int, end: int) -> list[dict]:
        self.log_calls.append((start, end))
        if self.fail_logs:
            raise RuntimeError("temporary failure")
        return []

    def get_block_timestamp(self, block: int) -> None:
        return None


def make_engine(client: FakeClient, directory: str) -> MonitorEngine:
    engine = MonitorEngine(client, EventStore(directory + "/events.sqlite3"), "0x" + "1" * 40, poll_interval=0)
    engine.start(start_block=1, resume=False)
    return engine


def test_incremental_polling_and_empty_results() -> None:
    with TemporaryDirectory() as directory:
        client = FakeClient()
        engine = make_engine(client, directory)
        assert engine.poll_once() == []
        client.latest = 11
        assert engine.poll_once() == []
        assert client.log_calls == [(1, 10), (11, 11)]
        assert engine.store.count() == 0
        engine.store.close()


def test_failed_query_preserves_cursor_and_recovers() -> None:
    with TemporaryDirectory() as directory:
        client = FakeClient()
        engine = make_engine(client, directory)
        client.fail_logs = True
        try:
            engine.poll_once()
        except RuntimeError:
            pass
        else:
            raise AssertionError("failed query did not propagate")
        assert engine.cursor == 0
        assert engine.stats.last_error == "temporary failure"
        client.fail_logs = False
        engine.poll_once(force=True)
        assert engine.cursor == 10
        assert engine.stats.last_error is None
        engine.store.close()


def test_restart_resumes_persisted_cursor() -> None:
    with TemporaryDirectory() as directory:
        client = FakeClient()
        first = make_engine(client, directory)
        first.poll_once()
        second = MonitorEngine(client, first.store, first.contract, poll_interval=0)
        second.start(resume=True)
        assert second.cursor == 10
        client.latest = 11
        second.poll_once()
        assert client.log_calls[-1] == (11, 11)
        first.store.close()


def test_reset_clears_events_and_cursor() -> None:
    with TemporaryDirectory() as directory:
        client = FakeClient()
        engine = make_engine(client, directory)
        engine.poll_once()
        engine.store.set_cursor(99)
        engine.store.reset()
        assert engine.store.get_cursor() is None
        assert engine.store.count() == 0
        engine.store.close()