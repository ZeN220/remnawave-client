import pytest

from remnawave import AsyncRemnawave, Remnawave
from remnawave.types import User
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport

BASE_URL = "https://panel.example.com"


def test_get_user_by_id(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    user = client.users.get_user_by_id(42)

    assert isinstance(user, User)
    assert sync_transport.requests[0].url == f"{BASE_URL}/api/users/42"
    assert sync_transport.requests[0].method == "GET"


@pytest.mark.parametrize("replies", ["GetUsersResponseDto"], indirect=True)
def test_query_params_are_passed(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    client.users.get_users(start=50, size=10)

    assert sync_transport.requests[0].params == {"start": 50, "size": 10}


def test_secret_repr(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    user = client.users.get_user_by_id(42)

    assert "trojan_password" not in repr(user)


async def test_async_group(async_transport: FakeAsyncTransport) -> None:
    client = AsyncRemnawave(BASE_URL, "secret", transport=async_transport)

    user = await client.users.get_user_by_id(42)

    assert isinstance(user, User)


@pytest.mark.parametrize("replies", ["GetUsersResponseDto"], indirect=True)
def test_iter_users_walks_pages(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    users = list(client.users.iter_users(page_size=1))

    assert len(users) == 1
    assert sync_transport.requests[0].params == {"start": 0, "size": 1}


@pytest.mark.parametrize("replies", ["GetUsersResponseDto"], indirect=True)
def test_iter_users_clamps_page_size(sync_transport: FakeSyncTransport) -> None:
    client = Remnawave(BASE_URL, "secret", transport=sync_transport)

    list(client.users.iter_users(page_size=99_999))

    assert sync_transport.requests[0].params["size"] == 1000
