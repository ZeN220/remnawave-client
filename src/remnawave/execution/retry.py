from typing import Protocol

from remnawave.exceptions import TransportError
from remnawave.http import Request, Response


class RetryPolicy(Protocol):
    def delay(
        self,
        attempt: int,
        request: Request,
        response: Response | None,
        error: TransportError | None,
    ) -> float | None: ...
