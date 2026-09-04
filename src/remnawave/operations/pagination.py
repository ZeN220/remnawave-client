from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Pagination:
    items_field: str
    total_field: str = "total"
    offset_param: str = "start"
    limit_param: str = "size"
    max_page_size: int = 100


class Paginator:
    __slots__ = ("_done", "_offset", "_page_size", "_pagination", "_query")

    def __init__(
        self,
        pagination: Pagination,
        page_size: int | None = None,
        query: dict[str, Any] | None = None,
    ) -> None:
        if page_size is not None and page_size < 1:
            message = "page_size must be >= 1"
            raise ValueError(message)
        self._pagination = pagination
        size = page_size or pagination.max_page_size
        self._page_size = min(size, pagination.max_page_size)
        self._query = dict(query or {})
        self._offset = 0
        self._done = False

    @property
    def done(self) -> bool:
        return self._done

    def next_query(self) -> dict[str, Any]:
        return {
            **self._query,
            self._pagination.offset_param: self._offset,
            self._pagination.limit_param: self._page_size,
        }

    def consume(self, page: object) -> list[Any]:
        items: list[Any] = getattr(page, self._pagination.items_field)
        total = getattr(page, self._pagination.total_field, None)

        self._offset += len(items)
        short_page = len(items) < self._page_size
        reached_total = total is not None and self._offset >= total
        self._done = short_page or reached_total
        return items
