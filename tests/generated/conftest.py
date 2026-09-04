import pytest

from remnawave.http import Response
from tests.execution.fakes import FakeAsyncTransport, FakeSyncTransport, Reply
from tests.generated.examples import example_body


@pytest.fixture
def replies(request: pytest.FixtureRequest) -> list[Reply]:
    dto: str = getattr(request, "param", "UserResponseDto")
    return [Response(status=200, content=example_body(dto))]


@pytest.fixture
def sync_transport(replies: list[Reply]) -> FakeSyncTransport:
    return FakeSyncTransport(replies)


@pytest.fixture
def async_transport(replies: list[Reply]) -> FakeAsyncTransport:
    return FakeAsyncTransport(replies)
