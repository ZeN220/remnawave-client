import random
from collections.abc import Sequence

from remnawave.exceptions import TransportError
from remnawave.http import Request, Response

from .retry import RetryPolicy

RETRYABLE_STATUSES = (429, 500, 502, 503, 504)

RETRYABLE_METHODS = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")


class ExponentialBackoff(RetryPolicy):
    def __init__(  # noqa: PLR0913
        self,
        attempts: int = 3,
        base: float = 0.5,
        max_delay: float = 8.0,
        *,
        statuses: Sequence[int] = RETRYABLE_STATUSES,
        methods: Sequence[str] = RETRYABLE_METHODS,
        jitter: bool = True,
    ) -> None:
        if attempts < 1:
            message = "attempts must be >= 1"
            raise ValueError(message)
        self._attempts = attempts
        self._base = base
        self._max_delay = max_delay
        self._statuses = frozenset(statuses)
        self._methods = frozenset(methods)
        self._jitter = jitter

    def delay(
        self,
        attempt: int,
        request: Request,
        response: Response | None,
        error: TransportError | None,
    ) -> float | None:
        if attempt >= self._attempts:
            return None

        if request.method.upper() not in self._methods:
            return None

        if error is not None:
            return self._backoff(attempt)

        if response is None or response.status not in self._statuses:
            return None

        after = _retry_after(response)
        return self._backoff(attempt) if after is None else after

    def _backoff(self, attempt: int) -> float:
        delay = min(self._base * 2.0 ** (attempt - 1), self._max_delay)
        if not self._jitter:
            return delay
        return delay * (0.5 + random.random() / 2)  # noqa: S311


def _retry_after(response: Response) -> float | None:
    raw = next(
        (v for k, v in response.headers.items() if k.lower() == "retry-after"),
        None,
    )
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None
