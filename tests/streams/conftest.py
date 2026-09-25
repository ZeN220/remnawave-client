from typing import cast

import fakeredis
import pytest
from redis.typing import EncodableT, FieldT

from remnawave.streams.messages import UserUsageMessage
from remnawave.streams.redis import AsyncStreamConsumer, StreamConsumer
from remnawave.streams.stream import USER_USAGE

TS = "2026-09-24T20:00:00.000Z"


def usage(records: str = "42:1024") -> dict[str, str]:
    return {"v": "1", "nodeId": "3", "ts": TS, "records": records}


SUBSCRIPTION_REQUEST = {
    "v": "1",
    "userId": "42",
    "requestAt": TS,
    "srrResponseType": "XRAY_JSON",
}
NODE_SNAPSHOT = {"v": "1", "nodeId": "3", "ts": TS, "users": "[]"}


def add(
    redis: fakeredis.FakeRedis,
    fields: dict[str, str],
    key: str = USER_USAGE.key,
) -> str:
    return _text(redis.xadd(key, _fields(fields)))


async def async_add(
    redis: fakeredis.FakeAsyncRedis,
    fields: dict[str, str],
    key: str = USER_USAGE.key,
) -> str:
    return _text(await redis.xadd(key, _fields(fields)))


def _fields(fields: dict[str, str]) -> dict[FieldT, EncodableT]:
    return cast("dict[FieldT, EncodableT]", fields)


def _text(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture
def async_redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
def consumer(
    redis: fakeredis.FakeRedis,
) -> StreamConsumer[UserUsageMessage]:
    return StreamConsumer(redis, USER_USAGE, "billing", "w1", block=0.01)


@pytest.fixture
def async_consumer(
    async_redis: fakeredis.FakeAsyncRedis,
) -> AsyncStreamConsumer[UserUsageMessage]:
    return AsyncStreamConsumer(
        async_redis, USER_USAGE, "billing", "w1", block=0.01
    )
