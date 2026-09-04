from collections.abc import AsyncIterator, Iterator
from typing import Any

from remnawave.execution.executor import AsyncExecutor, SyncExecutor
from remnawave.operations import Operation, Pagination, Paginator


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


def _pagination(operation: Operation[Any]) -> Pagination:
    if operation.pagination is None:
        message = f"{operation.method} {operation.path} is not paginated"
        raise TypeError(message)
    return operation.pagination
