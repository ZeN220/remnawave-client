import pytest

from remnawave.exceptions import NetworkError, ServerError
from remnawave.execution import AsyncExecutor, AsyncGroup
from remnawave.http import Response
from remnawave.operations import Operation, Pagination
from tests.execution.fakes import FakeAsyncTransport, Reply
from tests.samples import Sample, SamplePage

GET_USER: Operation[Sample] = Operation("GET", "/api/users/{uuid}", Sample)
LIST_USERS: Operation[SamplePage] = Operation(
    "GET",
    "/api/users",
    SamplePage,
    pagination=Pagination(items_field="users", max_page_size=100),
)


async def test_result_is_parsed(async_executor: AsyncExecutor) -> None:
    user = await async_executor.execute(GET_USER, path={"uuid": "abc"})

    assert user.short_uuid == "kR3nQ"


class TestRetries:
    @pytest.fixture
    def replies(self, payload: bytes) -> list[Reply]:
        body = b'{"response":' + payload + b"}"
        return [Response(status=503), Response(status=200, content=body)]

    async def test_retries_then_succeeds(
        self,
        async_executor: AsyncExecutor,
        async_transport: FakeAsyncTransport,
    ) -> None:
        user = await async_executor.execute(GET_USER, path={"uuid": "abc"})

        assert user.short_uuid == "kR3nQ"
        assert len(async_transport.requests) == 2


class TestErrors:
    @pytest.fixture
    def replies(self) -> list[Reply]:
        return [NetworkError("boom")] * 3

    async def test_error_after_retries(
        self,
        async_executor: AsyncExecutor,
        async_transport: FakeAsyncTransport,
    ) -> None:
        with pytest.raises(NetworkError):
            await async_executor.execute(GET_USER, path={"uuid": "abc"})

        assert len(async_transport.requests) == 3


class TestServerError:
    @pytest.fixture
    def replies(self) -> list[Reply]:
        return [Response(status=500, content=b'{"message":"boom"}')] * 3

    async def test_api_error(self, async_executor: AsyncExecutor) -> None:
        with pytest.raises(ServerError):
            await async_executor.execute(GET_USER, path={"uuid": "abc"})


class TestPagination:
    @pytest.fixture
    def replies(self, payload: bytes) -> list[Reply]:
        page = b'{"response":{"total":2,"users":[' + payload + b"]}}"
        return [Response(status=200, content=page)] * 2

    async def test_async_paginate(
        self,
        async_executor: AsyncExecutor,
        async_transport: FakeAsyncTransport,
    ) -> None:
        group = AsyncGroup(async_executor)

        collected = [
            user
            async for user in group._paginate(LIST_USERS, 1)  # noqa: SLF001
        ]

        assert len(collected) == 2
        assert [r.params["start"] for r in async_transport.requests] == [0, 1]

    async def test_not_paginated(self, async_executor: AsyncExecutor) -> None:
        group = AsyncGroup(async_executor)

        with pytest.raises(TypeError, match="not paginated"):
            [x async for x in group._paginate(GET_USER)]  # noqa: SLF001
