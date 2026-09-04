from collections.abc import Callable

import httpx
import pytest

from remnawave.http import HttpxAsync, HttpxSync

Reply = httpx.Response | Exception
Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def url() -> str:
    return "https://panel.example.com/api/users"


@pytest.fixture
def sent() -> list[httpx.Request]:
    return []


@pytest.fixture
def reply(request: pytest.FixtureRequest) -> Reply:
    value: Reply = getattr(request, "param", httpx.Response(200))
    return value


@pytest.fixture
def handler(sent: list[httpx.Request], reply: Reply) -> Handler:
    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(
            reply.status_code,
            headers=reply.headers,
            content=reply.content,
        )

    return handle


@pytest.fixture
def client(handler: Handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def async_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def sync_transport(client: httpx.Client) -> HttpxSync:
    return HttpxSync(client)


@pytest.fixture
def async_transport(async_client: httpx.AsyncClient) -> HttpxAsync:
    return HttpxAsync(async_client)
