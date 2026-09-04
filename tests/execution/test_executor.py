import pytest

from remnawave.exceptions import NetworkError, ServerError
from remnawave.execution import BearerAuth, SyncExecutor
from remnawave.http import Response
from remnawave.operations import (
    NoContentOperation,
    Operation,
    RawOperation,
    RequestBuilder,
    ResponseParser,
)
from tests.execution.fakes import FakeSyncTransport, Reply
from tests.samples import Sample

GET_USER: Operation[Sample] = Operation("GET", "/api/users/{uuid}", Sample)
DELETE_USER = NoContentOperation("DELETE", "/api/users/{uuid}")
GET_SUB = RawOperation("GET", "/api/sub/{shortUuid}")
POST_BULK: Operation[Sample] = Operation("POST", "/api/users/bulk", Sample)


def test_result_is_parsed(executor: SyncExecutor) -> None:
    user = executor.execute(GET_USER, path={"uuid": "abc"})

    assert user.short_uuid == "kR3nQ"


def test_request_is_built(
    executor: SyncExecutor,
    sync_transport: FakeSyncTransport,
    base_url: str,
) -> None:
    executor.execute(GET_USER, path={"uuid": "abc"}, query={"deep": True})

    request = sync_transport.requests[0]
    assert request.url == f"{base_url}/api/users/abc"
    assert request.params == {"deep": True}


def test_auth_header_is_added(
    sync_transport: FakeSyncTransport,
    builder: RequestBuilder,
    parser: ResponseParser,
) -> None:
    executor = SyncExecutor(
        sync_transport,
        builder,
        parser,
        auth=BearerAuth("secret"),
    )

    executor.execute(GET_USER, path={"uuid": "abc"})

    headers = sync_transport.requests[0].headers
    assert headers["Authorization"] == "Bearer secret"


def test_without_auth_no_header(
    executor: SyncExecutor,
    sync_transport: FakeSyncTransport,
) -> None:
    executor.execute(GET_USER, path={"uuid": "abc"})

    assert "Authorization" not in sync_transport.requests[0].headers


def test_timeout_reaches_transport(
    sync_transport: FakeSyncTransport,
    builder: RequestBuilder,
    parser: ResponseParser,
) -> None:
    executor = SyncExecutor(sync_transport, builder, parser, timeout=2.5)

    executor.execute(GET_USER, path={"uuid": "abc"})

    assert sync_transport.timeouts == [2.5]


@pytest.mark.parametrize(
    "replies",
    [[Response(status=204)]],
    indirect=True,
)
def test_no_content(executor: SyncExecutor) -> None:
    assert executor.execute(DELETE_USER, path={"uuid": "abc"}) is None


@pytest.mark.parametrize(
    "replies",
    [[Response(status=200, content=b"proxies: []")]],
    indirect=True,
)
def test_raw_body(executor: SyncExecutor) -> None:
    body = executor.execute(GET_SUB, path={"shortUuid": "abc"})

    assert body == b"proxies: []"


class TestRetries:
    @pytest.fixture
    def replies(self, payload: bytes) -> list[Reply]:
        body = b'{"response":' + payload + b"}"
        return [Response(status=503), Response(status=200, content=body)]

    def test_retries_then_succeeds(
        self,
        executor: SyncExecutor,
        sync_transport: FakeSyncTransport,
    ) -> None:
        user = executor.execute(GET_USER, path={"uuid": "abc"})

        assert user.short_uuid == "kR3nQ"
        assert len(sync_transport.requests) == 2


class TestGivesUp:
    @pytest.fixture
    def replies(self) -> list[Reply]:
        return [Response(status=503)] * 3

    def test_last_response_is_raised(
        self,
        executor: SyncExecutor,
        sync_transport: FakeSyncTransport,
    ) -> None:
        with pytest.raises(ServerError):
            executor.execute(GET_USER, path={"uuid": "abc"})

        assert len(sync_transport.requests) == 3


class TestTransportErrors:
    @pytest.fixture
    def replies(self) -> list[Reply]:
        return [NetworkError("boom")] * 3

    def test_error_is_raised_after_retries(
        self,
        executor: SyncExecutor,
        sync_transport: FakeSyncTransport,
    ) -> None:
        with pytest.raises(NetworkError):
            executor.execute(GET_USER, path={"uuid": "abc"})

        assert len(sync_transport.requests) == 3


class TestNonIdempotent:
    @pytest.fixture
    def replies(self) -> list[Reply]:
        return [Response(status=503)]

    def test_post_is_not_retried(
        self,
        executor: SyncExecutor,
        sync_transport: FakeSyncTransport,
    ) -> None:
        with pytest.raises(ServerError):
            executor.execute(POST_BULK)

        assert len(sync_transport.requests) == 1
