import pytest

from remnawave.operations import Pagination, Paginator

PAGINATION = Pagination(items_field="users", max_page_size=100)


class Page:
    def __init__(self, users: list[int], total: int) -> None:
        self.users = users
        self.total = total


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="page_size"):
        Paginator(PAGINATION, page_size=0)


def test_default_page_size_is_the_maximum() -> None:
    paginator = Paginator(PAGINATION)

    assert paginator.next_query() == {"start": 0, "size": 100}


def test_extra_query_is_kept() -> None:
    paginator = Paginator(PAGINATION, page_size=5, query={"tag": "vip"})

    assert paginator.next_query() == {"tag": "vip", "start": 0, "size": 5}


def test_full_page_continues() -> None:
    paginator = Paginator(PAGINATION, page_size=2)

    items = paginator.consume(Page([1, 2], total=4))

    assert items == [1, 2]
    assert paginator.done is False
    assert paginator.next_query()["start"] == 2


def test_reaching_total_stops() -> None:
    paginator = Paginator(PAGINATION, page_size=2)
    paginator.consume(Page([1, 2], total=2))

    assert paginator.done is True


def test_empty_page_stops() -> None:
    paginator = Paginator(PAGINATION, page_size=2)

    assert paginator.consume(Page([], total=99)) == []
    assert paginator.done is True
