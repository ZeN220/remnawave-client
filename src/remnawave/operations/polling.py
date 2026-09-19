from typing import TypeVar

from remnawave.exceptions import JobFailedError, JobTimeoutError

T = TypeVar("T")


class Poller:
    __slots__ = ("_deadline", "_interval", "_job_id")

    def __init__(
        self,
        job_id: str,
        started: float,
        interval: float,
        timeout: float | None,
    ) -> None:
        if interval <= 0:
            message = "interval must be > 0"
            raise ValueError(message)
        if timeout is not None and timeout < 0:
            message = "timeout must be >= 0"
            raise ValueError(message)
        self._job_id = job_id
        self._interval = interval
        self._deadline = None if timeout is None else started + timeout

    def settle(
        self, *, completed: bool, failed: bool, value: T | None
    ) -> T | None:
        if failed:
            message = f"job {self._job_id} failed"
            raise JobFailedError(message, self._job_id)
        if not completed:
            return None
        if value is None:
            message = f"job {self._job_id} completed without a result"
            raise JobFailedError(message, self._job_id)
        return value

    def delay(self, now: float) -> float:
        if self._deadline is None:
            return self._interval
        left = self._deadline - now
        if left <= 0:
            message = f"job {self._job_id} did not finish in time"
            raise JobTimeoutError(message, self._job_id)
        return min(self._interval, left)
