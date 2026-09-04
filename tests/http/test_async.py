import httpx
import pytest

from remnawave.exceptions import RequestTimeoutError
from remnawave.http import HttpxAsync, HttpxSync, Request


@pytest.mark.parametrize(
    "reply",
    [httpx.Response(201, headers={"X-Trace": "abc"}, content=b"body")],
    indirect=True,
)
async def test_same_result(
    sync_transport: HttpxSync,
    async_transport: HttpxAsync,
    sent: list[httpx.Request],
    url: str,
) -> None:
    request = Request(method="PATCH", url=url, params={"a": 1}, content=b"{}")

    sync_response = sync_transport.send(request, timeout=1.0)
    async_response = await async_transport.send(request, timeout=1.0)

    assert sync_response == async_response
    assert str(sent[0].url) == str(sent[1].url)
    assert sent[0].content == sent[1].content


@pytest.mark.parametrize("reply", [httpx.ConnectTimeout("nope")], indirect=True)
async def test_timeout(async_transport: HttpxAsync, url: str) -> None:
    with pytest.raises(RequestTimeoutError):
        await async_transport.send(Request(method="GET", url=url), timeout=0.01)
