import httpx

from remnawave.http import HttpxSync, Request


def test_all_fields_sent(
    sync_transport: HttpxSync,
    sent: list[httpx.Request],
    url: str,
) -> None:
    sync_transport.send(
        Request(
            method="POST",
            url=url,
            params={"start": 0, "size": 25},
            headers={"Authorization": "Bearer secret"},
            content=b'{"a":1}',
        ),
        timeout=5.0,
    )

    assert sent[0].method == "POST"
    assert str(sent[0].url) == f"{url}?start=0&size=25"
    assert sent[0].headers["Authorization"] == "Bearer secret"
    assert sent[0].content == b'{"a":1}'


def test_no_params_no_query(
    sync_transport: HttpxSync,
    sent: list[httpx.Request],
    url: str,
) -> None:
    sync_transport.send(Request(method="GET", url=url), timeout=None)

    assert str(sent[0].url) == url
    assert sent[0].content == b""
