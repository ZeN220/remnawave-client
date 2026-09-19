import pytest

from remnawave.exceptions import JobFailedError, JobTimeoutError
from remnawave.operations import Poller


@pytest.fixture
def poller() -> Poller:
    return Poller("j1", started=100.0, interval=2.0, timeout=10.0)


def test_interval_must_be_positive() -> None:
    with pytest.raises(ValueError, match="interval"):
        Poller("j1", started=0, interval=0, timeout=None)


def test_timeout_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="timeout"):
        Poller("j1", started=0, interval=1, timeout=-1)


def test_pending(poller: Poller) -> None:
    assert poller.settle(completed=False, failed=False, value=None) is None


def test_completed(poller: Poller) -> None:
    assert poller.settle(completed=True, failed=False, value=42) == 42


def test_failed(poller: Poller) -> None:
    with pytest.raises(JobFailedError, match="j1 failed") as caught:
        poller.settle(completed=True, failed=True, value=42)

    assert caught.value.job_id == "j1"


def test_completed_without_result(poller: Poller) -> None:
    with pytest.raises(JobFailedError, match="without a result"):
        poller.settle(completed=True, failed=False, value=None)


def test_delay_without_timeout() -> None:
    poller = Poller("j1", started=0, interval=2.0, timeout=None)

    assert poller.delay(now=1_000_000.0) == 2.0


def test_delay_is_the_interval(poller: Poller) -> None:
    assert poller.delay(now=101.0) == 2.0


def test_delay_does_not_overshoot_the_deadline(poller: Poller) -> None:
    assert poller.delay(now=109.5) == 0.5


def test_deadline(poller: Poller) -> None:
    with pytest.raises(JobTimeoutError, match="j1") as caught:
        poller.delay(now=110.0)

    assert caught.value.job_id == "j1"
