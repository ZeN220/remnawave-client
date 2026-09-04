import httpx

from remnawave.http import HttpxAsync, HttpxSync


def test_close(client: httpx.Client, sync_transport: HttpxSync) -> None:
    sync_transport.close()

    assert client.is_closed is True


async def test_aclose(
    async_client: httpx.AsyncClient,
    async_transport: HttpxAsync,
) -> None:
    await async_transport.aclose()

    assert async_client.is_closed is True


def test_default_client() -> None:
    transport = HttpxSync()

    transport.close()
