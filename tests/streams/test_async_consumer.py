import fakeredis
import pytest
from redis import ResponseError

from remnawave.exceptions import StreamMessageError
from remnawave.streams import (
    NodeConnectionsMessage,
    SubscriptionRequestMessage,
    UserUsageMessage,
)
from remnawave.streams.redis import AsyncRedisStreams, AsyncStreamConsumer
from remnawave.streams.stream import (
    NODE_CONNECTIONS,
    SUBSCRIPTION_REQUESTS,
    USER_USAGE,
)
from tests.streams.conftest import (
    NODE_SNAPSHOT,
    SUBSCRIPTION_REQUEST,
    async_add,
    usage,
)

KEY = USER_USAGE.key


async def test_reads_and_acks(
    async_redis: fakeredis.FakeAsyncRedis,
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    await async_consumer.create_group()
    await async_consumer.create_group()
    entry_id = await async_add(async_redis, usage())

    (entry,) = await async_consumer.read()
    await async_consumer.ack(entry)

    assert entry.id == entry_id
    assert (await async_redis.xpending(KEY, "billing"))["pending"] == 0


async def test_creates_group_on_read(
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    assert await async_consumer.read() == []


async def test_create_group_error(
    async_redis: fakeredis.FakeAsyncRedis,
) -> None:
    await async_redis.set(KEY, "not a stream")
    consumer = AsyncStreamConsumer(async_redis, USER_USAGE, "billing", "w1")

    with pytest.raises(ResponseError):
        await consumer.create_group()


async def test_trimmed_pending_entries_are_dropped(
    async_redis: fakeredis.FakeAsyncRedis,
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    await async_consumer.create_group()
    entry_id = await async_add(async_redis, usage())
    await async_consumer.read()
    await async_redis.xdel(KEY, entry_id)

    restarted = AsyncStreamConsumer(
        async_redis, USER_USAGE, "billing", "w1", block=0.01
    )

    assert await restarted.read() == []
    assert (await async_redis.xpending(KEY, "billing"))["pending"] == 0


async def test_broken_message(
    async_redis: fakeredis.FakeAsyncRedis,
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    await async_consumer.create_group()
    bad = await async_add(async_redis, {**usage(), "v": "2"})

    with pytest.raises(StreamMessageError) as error:
        await async_consumer.read()

    assert error.value.entry_id == bad


async def test_iterate(
    async_redis: fakeredis.FakeAsyncRedis,
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    await async_consumer.create_group()
    ids = [await async_add(async_redis, usage()) for _ in range(2)]

    seen = []
    async for entry in async_consumer:
        seen.append(entry.id)
        if len(seen) == len(ids):
            break

    assert seen == ids


async def test_auto_ack(async_redis: fakeredis.FakeAsyncRedis) -> None:
    consumer = AsyncStreamConsumer(
        async_redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    await consumer.create_group()
    await async_add(async_redis, usage())
    assert len(await consumer.read()) == 1
    assert (await async_redis.xpending(KEY, "billing"))["pending"] == 1

    await consumer.read()
    assert (await async_redis.xpending(KEY, "billing"))["pending"] == 0


async def test_factory(async_redis: fakeredis.FakeAsyncRedis) -> None:
    streams = AsyncRedisStreams(async_redis, "billing", "w1")
    users = streams.user_usage(start_id="0", block=0.01)
    requests = streams.subscription_requests(start_id="0", block=0.01)
    nodes = streams.node_connections(start_id="0", block=0.01)
    await async_add(async_redis, usage())
    await async_add(
        async_redis, SUBSCRIPTION_REQUEST, SUBSCRIPTION_REQUESTS.key
    )
    await async_add(async_redis, NODE_SNAPSHOT, NODE_CONNECTIONS.key)

    assert isinstance((await users.read())[0].message, UserUsageMessage)
    assert isinstance(
        (await requests.read())[0].message, SubscriptionRequestMessage
    )
    assert isinstance((await nodes.read())[0].message, NodeConnectionsMessage)


async def test_ack_nothing(
    async_consumer: AsyncStreamConsumer[UserUsageMessage],
) -> None:
    await async_consumer.create_group()

    await async_consumer.ack()


async def test_auto_ack_retries_failed_ack(
    async_redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumer = AsyncStreamConsumer(
        async_redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    await consumer.create_group()
    await async_add(async_redis, usage())
    await consumer.read()

    with monkeypatch.context() as patched:
        patched.setattr(async_redis, "xack", _fail)
        with pytest.raises(ConnectionError):
            await consumer.read()

    await consumer.read()
    assert (await async_redis.xpending(KEY, "billing"))["pending"] == 0


async def _fail(*_: object) -> None:
    raise ConnectionError
