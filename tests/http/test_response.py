import httpx
import pytest

from remnawave.http import HttpxSync, Request, Response


@pytest.mark.parametrize(
    "reply",
    [httpx.Response(404, headers={"X-Trace": "abc"}, content=b"nope")],
    indirect=True,
)
def test_status_headers_body(sync_transport: HttpxSync, url: str) -> None:
    response = sync_transport.send(Request(method="GET", url=url), timeout=None)

    assert isinstance(response, Response)
    assert response.status == 404
    assert response.headers["x-trace"] == "abc"
    assert response.content == b"nope"


@pytest.mark.parametrize("reply", [httpx.Response(500)], indirect=True)
def test_error_status_is_returned(sync_transport: HttpxSync, url: str) -> None:
    response = sync_transport.send(Request(method="GET", url=url), timeout=None)

    assert response.status == 500
