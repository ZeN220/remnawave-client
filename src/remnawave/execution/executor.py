import asyncio
import time
from dataclasses import replace
from typing import Any, TypeVar, overload

from remnawave.exceptions import TransportError
from remnawave.http import AsyncTransport, Request, Response, SyncTransport
from remnawave.operations import (
    AnyOperation,
    NoContentOperation,
    Operation,
    RawOperation,
    RequestBuilder,
    ResponseParser,
)

from .auth import Auth
from .retry import RetryPolicy

T = TypeVar("T")

DEFAULT_TIMEOUT = 30.0


class BaseExecutor:
    def __init__(
        self,
        builder: RequestBuilder,
        parser: ResponseParser,
        *,
        auth: Auth | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        self._builder = builder
        self._parser = parser
        self._auth = auth
        self._retry = retry
        self._timeout = timeout

    def set_auth(self, auth: Auth | None) -> None:
        self._auth = auth

    def _request(
        self,
        operation: AnyOperation,
        path: dict[str, Any] | None,
        query: dict[str, Any] | None,
        body: object,
    ) -> Request:
        request = self._builder.build(operation, path, query, body)
        if self._auth is None:
            return request
        return replace(
            request,
            headers={**request.headers, **self._auth.headers()},
        )

    def _delay(
        self,
        attempt: int,
        request: Request,
        response: Response | None,
        error: TransportError | None,
    ) -> float | None:
        if self._retry is None:
            return None
        return self._retry.delay(attempt, request, response, error)


class SyncExecutor(BaseExecutor):
    def __init__(  # noqa: PLR0913
        self,
        transport: SyncTransport,
        builder: RequestBuilder,
        parser: ResponseParser,
        *,
        auth: Auth | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(
            builder,
            parser,
            auth=auth,
            retry=retry,
            timeout=timeout,
        )
        self._transport = transport

    @overload
    def execute(
        self,
        operation: NoContentOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> None: ...

    @overload
    def execute(
        self,
        operation: RawOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> bytes: ...

    @overload
    def execute(
        self,
        operation: "Operation[T]",
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> T: ...

    def execute(
        self,
        operation: AnyOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> Any:
        request = self._request(operation, path, query, body)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._transport.send(request, self._timeout)
            except TransportError as exc:
                delay = self._delay(attempt, request, None, exc)
                if delay is None:
                    raise
                time.sleep(delay)
                continue

            delay = self._delay(attempt, request, response, None)
            if delay is None:
                return self._parser.parse(operation, response)
            time.sleep(delay)

    def close(self) -> None:
        self._transport.close()


class AsyncExecutor(BaseExecutor):
    def __init__(  # noqa: PLR0913
        self,
        transport: AsyncTransport,
        builder: RequestBuilder,
        parser: ResponseParser,
        *,
        auth: Auth | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(
            builder,
            parser,
            auth=auth,
            retry=retry,
            timeout=timeout,
        )
        self._transport = transport

    @overload
    async def execute(
        self,
        operation: NoContentOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> None: ...

    @overload
    async def execute(
        self,
        operation: RawOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> bytes: ...

    @overload
    async def execute(
        self,
        operation: "Operation[T]",
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> T: ...

    async def execute(
        self,
        operation: AnyOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> Any:
        request = self._request(operation, path, query, body)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self._transport.send(request, self._timeout)
            except TransportError as exc:
                delay = self._delay(attempt, request, None, exc)
                if delay is None:
                    raise
                await asyncio.sleep(delay)
                continue

            delay = self._delay(attempt, request, response, None)
            if delay is None:
                return self._parser.parse(operation, response)
            await asyncio.sleep(delay)

    async def aclose(self) -> None:
        await self._transport.aclose()
