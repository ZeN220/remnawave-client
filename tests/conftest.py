from datetime import UTC, datetime

import pytest

from tests.samples import Nested, Sample


@pytest.fixture
def payload() -> bytes:
    return (
        b'{"id":1,"shortUuid":"kR3nQ",'
        b'"createdAt":"2026-01-01T00:00:00.000Z",'
        b'"nested":{"usedBytes":10,"onlineAt":null}}'
    )


@pytest.fixture
def sample() -> Sample:
    return Sample(
        id=1,
        short_uuid="kR3nQ",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        nested=Nested(used_bytes=10, online_at=None),
    )
