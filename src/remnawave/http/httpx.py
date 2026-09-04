from typing import Any

import httpx

from remnawave.exceptions import NetworkError, RequestTimeoutError

from .transport import AsyncTransport, Request, Response, SyncTransport


class HttpxSync(SyncTransport):
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()

    def send(self, request: Request, timeout: float | None) -> Response:
        try:
            response = self._client.request(**_to_httpx(request, timeout))
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(str(exc)) from exc
        return _from_httpx(response)

    def close(self) -> None:
        self._client.close()


class HttpxAsync(AsyncTransport):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient()

    async def send(self, request: Request, timeout: float | None) -> Response:
        try:
            response = await self._client.request(**_to_httpx(request, timeout))
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(str(exc)) from exc
        return _from_httpx(response)

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_httpx(request: Request, timeout: float | None) -> dict[str, Any]:
    return {
        "method": request.method,
        "url": request.url,
        "params": request.params or None,
        "headers": request.headers,
        "content": request.content,
        "timeout": timeout,
    }


def _from_httpx(response: httpx.Response) -> Response:
    return Response(
        status=response.status_code,
        headers=dict(response.headers),
        content=response.content,
    )
