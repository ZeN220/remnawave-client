import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

from remnawave.execution.executor import AsyncExecutor, SyncExecutor
from remnawave.operations import (
    JobStatus,
    Operation,
    Pagination,
    Paginator,
    Poller,
)

T = TypeVar("T")

# Путь опроса статуса у всех задач панели параметризован одним jobId.
JOB_PARAM = "jobId"


class SyncGroup:
    def __init__(self, executor: SyncExecutor) -> None:
        self._executor = executor

    def _paginate(
        self,
        operation: Operation[Any],
        page_size: int | None = None,
        query: dict[str, Any] | None = None,
    ) -> Iterator[Any]:
        paginator = Paginator(_pagination(operation), page_size, query)
        while not paginator.done:
            page = self._executor.execute(
                operation,
                query=paginator.next_query(),
            )
            yield from paginator.consume(page)

    def _wait(  # noqa: PLR0913
        self,
        start: Operation[Any],
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
        *,
        result: Operation[JobStatus[T]],
        interval: float,
        timeout: float | None,
    ) -> T:
        job = self._executor.execute(start, path, query, body)
        poller = Poller(job.job_id, time.monotonic(), interval, timeout)
        while True:
            status = self._executor.execute(
                result,
                path={JOB_PARAM: job.job_id},
            )
            value = poller.settle(
                completed=status.is_completed,
                failed=status.is_failed,
                value=status.result,
            )
            if value is not None:
                return value
            time.sleep(poller.delay(time.monotonic()))


class AsyncGroup:
    def __init__(self, executor: AsyncExecutor) -> None:
        self._executor = executor

    async def _paginate(
        self,
        operation: Operation[Any],
        page_size: int | None = None,
        query: dict[str, Any] | None = None,
    ) -> AsyncIterator[Any]:
        paginator = Paginator(_pagination(operation), page_size, query)
        while not paginator.done:
            page = await self._executor.execute(
                operation,
                query=paginator.next_query(),
            )
            for item in paginator.consume(page):
                yield item

    async def _wait(  # noqa: PLR0913
        self,
        start: Operation[Any],
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
        *,
        result: Operation[JobStatus[T]],
        interval: float,
        timeout: float | None,
    ) -> T:
        job = await self._executor.execute(start, path, query, body)
        poller = Poller(job.job_id, time.monotonic(), interval, timeout)
        while True:
            status = await self._executor.execute(
                result,
                path={JOB_PARAM: job.job_id},
            )
            value = poller.settle(
                completed=status.is_completed,
                failed=status.is_failed,
                value=status.result,
            )
            if value is not None:
                return value
            await asyncio.sleep(poller.delay(time.monotonic()))


def _pagination(operation: Operation[Any]) -> Pagination:
    if operation.pagination is None:
        message = f"{operation.method} {operation.path} is not paginated"
        raise TypeError(message)
    return operation.pagination
