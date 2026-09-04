from collections import deque
from collections.abc import Sequence

from remnawave.http import Request, Response, SyncTransport
from remnawave.http.transport import AsyncTransport

Reply = Response | Exception


class FakeSyncTransport(SyncTransport):
    def __init__(self, replies: Sequence[Reply]) -> None:
        self._replies: deque[Reply] = deque(replies)
        self.requests: list[Request] = []
        self.timeouts: list[float | None] = []
        self.closed = False

    def send(self, request: Request, timeout: float | None) -> Response:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return _reply(self._replies)

    def close(self) -> None:
        self.closed = True


class FakeAsyncTransport(AsyncTransport):
    def __init__(self, replies: Sequence[Reply]) -> None:
        self._replies: deque[Reply] = deque(replies)
        self.requests: list[Request] = []
        self.timeouts: list[float | None] = []
        self.closed = False

    async def send(self, request: Request, timeout: float | None) -> Response:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return _reply(self._replies)

    async def aclose(self) -> None:
        self.closed = True


def _reply(replies: deque[Reply]) -> Response:
    if not replies:
        message = "unexpected request"
        raise AssertionError(message)
    reply = replies.popleft()
    if isinstance(reply, Exception):
        raise reply
    return reply
