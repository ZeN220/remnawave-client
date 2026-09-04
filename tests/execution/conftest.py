import pytest

from remnawave.execution import AsyncExecutor, ExponentialBackoff, SyncExecutor
from remnawave.http import Response
from remnawave.operations import RequestBuilder, ResponseParser
from remnawave.serialization import AdaptixSerializer
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport, Reply

BASE_URL = "https://panel.example.com"


@pytest.fixture
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def replies(request: pytest.FixtureRequest, payload: bytes) -> list[Reply]:
    default = [Response(status=200, content=b'{"response":' + payload + b"}")]
    value: list[Reply] = getattr(request, "param", default)
    return value


@pytest.fixture
def sync_transport(replies: list[Reply]) -> FakeSyncTransport:
    return FakeSyncTransport(replies)


@pytest.fixture
def async_transport(replies: list[Reply]) -> FakeAsyncTransport:
    return FakeAsyncTransport(replies)


@pytest.fixture
def builder(base_url: str) -> RequestBuilder:
    return RequestBuilder(base_url, AdaptixSerializer())


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser(AdaptixSerializer())


@pytest.fixture
def retry() -> ExponentialBackoff:
    return ExponentialBackoff(attempts=3, base=0, jitter=False)


@pytest.fixture
def executor(
    sync_transport: FakeSyncTransport,
    builder: RequestBuilder,
    parser: ResponseParser,
    retry: ExponentialBackoff,
) -> SyncExecutor:
    return SyncExecutor(sync_transport, builder, parser, retry=retry)


@pytest.fixture
def async_executor(
    async_transport: FakeAsyncTransport,
    builder: RequestBuilder,
    parser: ResponseParser,
    retry: ExponentialBackoff,
) -> AsyncExecutor:
    return AsyncExecutor(async_transport, builder, parser, retry=retry)
