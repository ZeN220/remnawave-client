import pytest

from remnawave.exceptions import JobFailedError, JobTimeoutError
from remnawave.execution import (
    AsyncExecutor,
    AsyncGroup,
    SyncExecutor,
    SyncGroup,
)
from remnawave.http import Response
from remnawave.operations import Operation
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport, Reply
from tests.samples import JobRef, JobStatus

START = Operation("POST", "/api/jobs/{id}", JobRef)
RESULT = Operation("GET", "/api/jobs/{jobId}", JobStatus)

STARTED = Response(status=200, content=b'{"response":{"jobId":"j1"}}')
PENDING = Response(
    status=200,
    content=b'{"response":{"isCompleted":false,"isFailed":false,"result":null}}',
)
DONE = Response(
    status=200,
    content=b'{"response":{"isCompleted":true,"isFailed":false,"result":42}}',
)
FAILED = Response(
    status=200,
    content=b'{"response":{"isCompleted":true,"isFailed":true,"result":null}}',
)


@pytest.fixture
def replies(request: pytest.FixtureRequest) -> list[Reply]:
    value: list[Reply] = getattr(request, "param", [STARTED, PENDING, DONE])
    return value


def test_waits_for_the_result(
    executor: SyncExecutor,
    sync_transport: FakeSyncTransport,
) -> None:
    group = SyncGroup(executor)

    value = group._wait(  # noqa: SLF001
        START,
        path={"id": 7},
        result=RESULT,
        interval=0.001,
        timeout=None,
    )

    assert value == 42
    urls = [r.url for r in sync_transport.requests]
    assert urls == [
        "https://panel.example.com/api/jobs/7",
        "https://panel.example.com/api/jobs/j1",
        "https://panel.example.com/api/jobs/j1",
    ]


@pytest.mark.parametrize("replies", [[STARTED, FAILED]], indirect=True)
def test_failed_job(executor: SyncExecutor) -> None:
    group = SyncGroup(executor)

    with pytest.raises(JobFailedError):
        group._wait(  # noqa: SLF001
            START,
            path={"id": 7},
            result=RESULT,
            interval=0.001,
            timeout=None,
        )


@pytest.mark.parametrize("replies", [[STARTED, PENDING]], indirect=True)
def test_timeout(executor: SyncExecutor) -> None:
    group = SyncGroup(executor)

    with pytest.raises(JobTimeoutError):
        group._wait(  # noqa: SLF001
            START,
            path={"id": 7},
            result=RESULT,
            interval=0.001,
            timeout=0,
        )


async def test_async_waits_for_the_result(
    async_executor: AsyncExecutor,
    async_transport: FakeAsyncTransport,
) -> None:
    group = AsyncGroup(async_executor)

    value = await group._wait(  # noqa: SLF001
        START,
        path={"id": 7},
        result=RESULT,
        interval=0.001,
        timeout=None,
    )

    assert value == 42
    assert len(async_transport.requests) == 3
