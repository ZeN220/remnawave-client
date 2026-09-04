from types import TracebackType
from typing import Self

from remnawave._generated.groups import AsyncGroups, SyncGroups
from remnawave._generated.renames import NAME_MAPPING
from remnawave.execution import (
    DEFAULT_TIMEOUT,
    AsyncExecutor,
    Auth,
    BearerAuth,
    ExponentialBackoff,
    RetryPolicy,
    SyncExecutor,
)
from remnawave.http import AsyncTransport, HttpxAsync, HttpxSync, SyncTransport
from remnawave.operations import RequestBuilder, ResponseParser
from remnawave.serialization import (
    AdaptixSerializer,
    Serializer,
    build_default_retort,
)


class Remnawave(SyncGroups):
    def __init__(  # noqa: PLR0913
        self,
        base_url: str,
        token: str | None = None,
        *,
        auth: Auth | None = None,
        transport: SyncTransport | None = None,
        serializer: Serializer | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        serializer = serializer or AdaptixSerializer(
            build_default_retort(*NAME_MAPPING),
        )
        self._executor = SyncExecutor(
            transport or HttpxSync(),
            RequestBuilder(base_url, serializer),
            ResponseParser(serializer),
            auth=_auth_from(token, auth),
            retry=retry if retry is not None else ExponentialBackoff(),
            timeout=timeout,
        )
        self._attach(self._executor)

    @property
    def executor(self) -> SyncExecutor:
        return self._executor

    def close(self) -> None:
        self._executor.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncRemnawave(AsyncGroups):
    def __init__(  # noqa: PLR0913
        self,
        base_url: str,
        token: str | None = None,
        *,
        auth: Auth | None = None,
        transport: AsyncTransport | None = None,
        serializer: Serializer | None = None,
        retry: RetryPolicy | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        serializer = serializer or AdaptixSerializer(
            build_default_retort(*NAME_MAPPING),
        )
        self._executor = AsyncExecutor(
            transport or HttpxAsync(),
            RequestBuilder(base_url, serializer),
            ResponseParser(serializer),
            auth=_auth_from(token, auth),
            retry=retry if retry is not None else ExponentialBackoff(),
            timeout=timeout,
        )
        self._attach(self._executor)

    @property
    def executor(self) -> AsyncExecutor:
        return self._executor

    async def aclose(self) -> None:
        await self._executor.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()


def _auth_from(token: str | None, auth: Auth | None) -> Auth | None:
    if token is not None and auth is not None:
        message = "pass either token or auth, not both"
        raise ValueError(message)
    if token is not None:
        return BearerAuth(token)
    return auth
