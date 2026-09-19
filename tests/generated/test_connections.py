import json
from uuid import UUID

import pytest

from remnawave import AsyncRemnawave, Remnawave
from remnawave.http import Response
from remnawave.types import (
    ConnectionsByUserResultResult,
    GeocheckByNodeBody,
    GeocheckByNodeResultResult,
)
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport, Reply
from tests.generated.examples import example_body

BASE_URL = "https://panel.example.com"
NODE = UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def replies(request: pytest.FixtureRequest) -> list[Reply]:
    job: str = request.param
    started = example_body(f"{job}ResponseDto")
    status = json.loads(example_body(f"{job}ResultResponseDto"))
    status["response"].update(isCompleted=False, isFailed=False)
    pending = json.dumps(status).encode()
    status["response"].update(isCompleted=True)
    done = json.dumps(status).encode()
    return [
        Response(status=200, content=started),
        Response(status=200, content=pending),
        Response(status=200, content=done),
    ]


@pytest.mark.parametrize("replies", ["ConnectionsByUser"], indirect=True)
def test_wait_connections_by_user(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    result = client.connections.wait_connections_by_user(7, interval=0.001)

    assert isinstance(result, ConnectionsByUserResultResult)
    assert [(r.method, r.url) for r in sync_transport.requests] == [
        ("POST", f"{BASE_URL}/api/connections/by-user/7"),
        ("GET", f"{BASE_URL}/api/connections/by-user/value"),
        ("GET", f"{BASE_URL}/api/connections/by-user/value"),
    ]


@pytest.mark.parametrize("replies", ["GeocheckByNode"], indirect=True)
async def test_wait_geocheck_by_node(
    async_transport: FakeAsyncTransport,
) -> None:
    client = AsyncRemnawave(BASE_URL, "secret", transport=async_transport)

    result = await client.connections.wait_geocheck_by_node(
        NODE,
        GeocheckByNodeBody(ip="1.1.1.1"),
        interval=0.001,
    )

    assert isinstance(result, GeocheckByNodeResultResult)
    assert async_transport.requests[0].url == (
        f"{BASE_URL}/api/connections/geocheck/{NODE}"
    )
    assert async_transport.requests[0].content == b'{"ip":"1.1.1.1"}'
