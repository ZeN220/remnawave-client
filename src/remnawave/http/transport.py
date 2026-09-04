from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Request:
    method: str
    url: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes | None = None


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes = b""


class SyncTransport(Protocol):
    def send(self, request: Request, timeout: float | None) -> Response: ...
    def close(self) -> None: ...


class AsyncTransport(Protocol):
    async def send(
        self, request: Request, timeout: float | None
    ) -> Response: ...
    async def aclose(self) -> None: ...
