import httpx
import pytest

from remnawave.exceptions import (
    NetworkError,
    RequestTimeoutError,
    TransportError,
)
from remnawave.http import HttpxAsync, HttpxSync, Request


@pytest.mark.parametrize(
    "reply",
    [httpx.ReadTimeout("too slow")],
    indirect=True,
)
def test_timeout(sync_transport: HttpxSync, url: str) -> None:
    with pytest.raises(RequestTimeoutError) as info:
        sync_transport.send(Request(method="GET", url=url), timeout=0.01)

    assert isinstance(info.value, TransportError)
    assert isinstance(info.value.__cause__, httpx.ReadTimeout)


@pytest.mark.parametrize(
    "reply",
    [httpx.ConnectError("refused")],
    indirect=True,
)
def test_connect_error(sync_transport: HttpxSync, url: str) -> None:
    with pytest.raises(NetworkError) as info:
        sync_transport.send(Request(method="GET", url=url), timeout=None)

    assert isinstance(info.value, TransportError)
    assert isinstance(info.value.__cause__, httpx.ConnectError)


@pytest.mark.parametrize(
    "reply",
    [httpx.ConnectError("refused")],
    indirect=True,
)
async def test_async_connect_error(
    async_transport: HttpxAsync, url: str
) -> None:
    with pytest.raises(NetworkError) as info:
        await async_transport.send(Request(method="GET", url=url), timeout=None)

    assert isinstance(info.value.__cause__, httpx.ConnectError)
