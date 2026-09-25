from itertools import islice
from typing import Any

import fakeredis
import pytest
from redis import ResponseError

from remnawave.exceptions import StreamMessageError
from remnawave.streams import (
    NodeConnectionsMessage,
    SubscriptionRequestMessage,
    UserUsageMessage,
)
from remnawave.streams.redis import RedisStreams, StreamConsumer, _entries
from remnawave.streams.stream import (
    NODE_CONNECTIONS,
    SUBSCRIPTION_REQUESTS,
    USER_USAGE,
)
from tests.streams.conftest import (
    NODE_SNAPSHOT,
    SUBSCRIPTION_REQUEST,
    add,
    usage,
)

KEY = USER_USAGE.key


def test_reads_new_entries(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    entry_id = add(redis, usage())

    (entry,) = consumer.read()

    assert entry.id == entry_id
    assert entry.message.records[0].total_bytes == 1024
    assert consumer.read() == []


def test_group_starts_at_the_end(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    add(redis, usage())

    assert consumer.read() == []


def test_start_id(redis: fakeredis.FakeRedis) -> None:
    add(redis, usage())
    consumer = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", start_id="0", block=0.01
    )

    assert len(consumer.read()) == 1


def test_create_group_twice(consumer: StreamConsumer[UserUsageMessage]) -> None:
    consumer.create_group()
    consumer.create_group()


def test_create_group_error(redis: fakeredis.FakeRedis) -> None:
    redis.set(KEY, "not a stream")
    consumer = StreamConsumer(redis, USER_USAGE, "billing", "w1")

    with pytest.raises(ResponseError):
        consumer.create_group()


def test_ack(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    add(redis, usage())
    add(redis, usage())
    first, second = consumer.read()

    consumer.ack(first, second.id)

    assert redis.xpending(KEY, "billing")["pending"] == 0


def test_ack_nothing(consumer: StreamConsumer[UserUsageMessage]) -> None:
    consumer.create_group()

    consumer.ack()


def test_pending_first_after_restart(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    add(redis, usage())
    add(redis, usage())
    delivered = consumer.read()
    consumer.ack(delivered[0])
    fresh = add(redis, usage())

    restarted = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", count=1, block=0.01
    )

    assert [e.id for e in restarted.read()] == [delivered[1].id]
    assert [e.id for e in restarted.read()] == [fresh]


def test_trimmed_pending_entries_are_dropped(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    entry_id = add(redis, usage())
    consumer.read()
    redis.xdel(KEY, entry_id)

    restarted = StreamConsumer(redis, USER_USAGE, "billing", "w1", block=0.01)

    assert restarted.read() == []
    assert redis.xpending(KEY, "billing")["pending"] == 0


def test_broken_message(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    good = add(redis, usage())
    bad = add(redis, {**usage(), "v": "2"})

    with pytest.raises(StreamMessageError) as error:
        consumer.read()
    assert error.value.entry_id == bad

    with pytest.raises(StreamMessageError):
        consumer.read()

    consumer.ack(bad)
    assert [e.id for e in consumer.read()] == [good]


def test_iterate(
    redis: fakeredis.FakeRedis,
    consumer: StreamConsumer[UserUsageMessage],
) -> None:
    consumer.create_group()
    ids = [add(redis, usage()) for _ in range(3)]

    assert [e.id for e in islice(consumer, 3)] == ids


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [({"count": 0}, "count"), ({"block": 0}, "block")],
)
def test_invalid_options(
    redis: fakeredis.FakeRedis, kwargs: dict[str, Any], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        StreamConsumer(redis, USER_USAGE, "billing", "w1", **kwargs)


@pytest.mark.parametrize(
    "reply",
    [
        [[b"k", [("1-0", {"v": "1"})]]],
        {b"k": [[("1-0", {"v": "1"})]]},
        {b"k": [("1-0", {"v": "1"})]},
    ],
)
def test_reply_shapes(reply: object) -> None:
    assert _entries(reply) == [("1-0", {"v": "1"})]


def test_empty_reply_shapes() -> None:
    assert _entries(None) == []
    assert _entries({}) == []
    assert _entries({b"k": []}) == []


def test_auto_ack_on_next_read(redis: fakeredis.FakeRedis) -> None:
    consumer = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    consumer.create_group()
    add(redis, usage())

    assert len(consumer.read()) == 1
    assert redis.xpending(KEY, "billing")["pending"] == 1

    consumer.read()
    assert redis.xpending(KEY, "billing")["pending"] == 0


def test_auto_ack_keeps_unfinished_entries(redis: fakeredis.FakeRedis) -> None:
    consumer = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    consumer.create_group()
    ids = [add(redis, usage()) for _ in range(2)]

    for entry in consumer:
        if entry.id == ids[1]:
            break

    assert redis.xpending(KEY, "billing")["pending"] == 2

    restarted = StreamConsumer(redis, USER_USAGE, "billing", "w1", block=0.01)
    assert [e.id for e in restarted.read()] == ids


def test_auto_ack_while_iterating(redis: fakeredis.FakeRedis) -> None:
    consumer = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    consumer.create_group()
    first = add(redis, usage())
    iterator = iter(consumer)

    assert next(iterator).id == first
    second = add(redis, usage())
    assert next(iterator).id == second
    assert redis.xpending(KEY, "billing")["pending"] == 1


def test_factory(redis: fakeredis.FakeRedis) -> None:
    streams = RedisStreams(redis, "billing", "w1")
    users = streams.user_usage(start_id="0", block=0.01)
    requests = streams.subscription_requests(start_id="0", block=0.01)
    nodes = streams.node_connections(start_id="0", block=0.01)
    add(redis, usage())
    add(redis, SUBSCRIPTION_REQUEST, SUBSCRIPTION_REQUESTS.key)
    add(redis, NODE_SNAPSHOT, NODE_CONNECTIONS.key)

    assert isinstance(users.read()[0].message, UserUsageMessage)
    assert isinstance(requests.read()[0].message, SubscriptionRequestMessage)
    assert isinstance(nodes.read()[0].message, NodeConnectionsMessage)


def test_default_name(redis: fakeredis.FakeRedis) -> None:
    consumer = RedisStreams(redis, "billing").user_usage(block=0.01)
    consumer.create_group()
    add(redis, usage())
    consumer.read()

    (info,) = redis.xinfo_consumers(KEY, "billing")
    assert info["name"] in {"default", b"default"}


def test_auto_ack_retries_failed_ack(
    redis: fakeredis.FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumer = StreamConsumer(
        redis, USER_USAGE, "billing", "w1", block=0.01, auto_ack=True
    )
    consumer.create_group()
    add(redis, usage())
    consumer.read()

    with monkeypatch.context() as patched:
        patched.setattr(redis, "xack", _fail)
        with pytest.raises(ConnectionError):
            consumer.read()

    consumer.read()
    assert redis.xpending(KEY, "billing")["pending"] == 0


def _fail(*_: object) -> None:
    raise ConnectionError
