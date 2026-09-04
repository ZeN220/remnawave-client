import pytest

from remnawave import AsyncRemnawave, Remnawave
from remnawave.execution import BearerAuth
from remnawave.http import Response
from remnawave.operations import Operation
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport
from tests.samples import Sample

GET_USER: Operation[Sample] = Operation("GET", "/api/users/{uuid}", Sample)


def test_token_and_auth_conflict() -> None:
    with pytest.raises(ValueError, match="not both"):
        Remnawave("https://panel.example.com", "t", auth=BearerAuth("t"))


def test_end_to_end(
    base_url: str,
    sync_transport: FakeSyncTransport,
) -> None:
    with Remnawave(base_url, "secret", transport=sync_transport) as client:
        user = client.executor.execute(GET_USER, path={"uuid": "abc"})

    assert user.short_uuid == "kR3nQ"
    headers = sync_transport.requests[0].headers
    assert headers["Authorization"] == "Bearer secret"
    assert sync_transport.closed is True


async def test_async_end_to_end(
    base_url: str,
    async_transport: FakeAsyncTransport,
) -> None:
    client = AsyncRemnawave(base_url, "secret", transport=async_transport)
    async with client:
        user = await client.executor.execute(GET_USER, path={"uuid": "abc"})

    assert user.short_uuid == "kR3nQ"
    assert async_transport.closed is True


@pytest.mark.parametrize(
    "replies",
    [[Response(status=204), Response(status=204)]],
    indirect=True,
)
def test_auth_can_be_swapped(
    base_url: str,
    sync_transport: FakeSyncTransport,
) -> None:
    client = Remnawave(base_url, "first", transport=sync_transport)

    client.users.delete_user(1)
    client.executor.set_auth(BearerAuth("second"))
    client.users.delete_user(1)

    sent = [r.headers["Authorization"] for r in sync_transport.requests]
    assert sent == ["Bearer first", "Bearer second"]


def test_auth_object_is_used(
    base_url: str,
    sync_transport: FakeSyncTransport,
) -> None:
    client = Remnawave(
        base_url,
        auth=BearerAuth("from-auth"),
        transport=sync_transport,
    )

    client.users.delete_user(1)

    headers = sync_transport.requests[0].headers
    assert headers["Authorization"] == "Bearer from-auth"
