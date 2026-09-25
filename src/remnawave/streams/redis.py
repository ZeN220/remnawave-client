from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Generic, TypedDict, TypeVar, Unpack

from redis import ResponseError

from remnawave.exceptions import SerializationError, StreamMessageError
from remnawave.streams.messages import (
    NodeConnectionsMessage,
    StreamEntry,
    SubscriptionRequestMessage,
    UserUsageMessage,
)
from remnawave.streams.stream import (
    NODE_CONNECTIONS,
    SUBSCRIPTION_REQUESTS,
    USER_USAGE,
    Stream,
)

if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis

T = TypeVar("T")

PENDING = "0"
NEW = ">"
# A consumer name must survive restarts, or the entries left pending under the
# old one are never read again; a single worker is fine with a fixed one.
DEFAULT_NAME = "default"

RawEntry = tuple[str | bytes, Any]


class ConsumerOptions(TypedDict, total=False):
    start_id: str
    count: int
    block: float
    auto_ack: bool


class _Cursor(Generic[T]):
    def __init__(  # noqa: PLR0913
        self,
        stream: Stream[T],
        *,
        group: str,
        name: str,
        start_id: str,
        count: int,
        block: float,
        auto_ack: bool,
    ) -> None:
        if count <= 0:
            message = "count must be > 0"
            raise ValueError(message)
        if block <= 0:
            message = "block must be > 0"
            raise ValueError(message)

        self.stream = stream
        self.group = group
        self.name = name
        self.start_id = start_id
        self.count = count
        self.block = block
        self.auto_ack = auto_ack
        self.group_ready = False
        self.position = PENDING

        # With auto_ack, the ids handed out by the previous read: they are
        # acknowledged once the caller comes back for more, and kept until
        # XACK succeeds so a failed one is retried on the next read.
        self.delivered: list[str] = []

    def request(self) -> dict[str, Any]:
        return {
            "groupname": self.group,
            "consumername": self.name,
            "streams": {self.stream.key: self.position},
            "count": self.count,
            "block": None if self.position != NEW else int(self.block * 1000),
        }

    def settle(
        self, reply: object
    ) -> tuple[list[StreamEntry[T]], list[str]] | None:
        raw = _entries(reply)
        if self.position != NEW:
            if not raw:
                self.position = NEW
                return None
            self.position = _text(raw[-1][0])

        entries: list[StreamEntry[T]] = []
        gone: list[str] = []
        for raw_id, fields in raw:
            entry_id = _text(raw_id)
            if not fields:
                gone.append(entry_id)
                continue
            try:
                message = self.stream.parse(fields)
            except SerializationError as exc:
                self.position = PENDING
                raise StreamMessageError(str(exc), entry_id) from exc
            entries.append(StreamEntry(entry_id, message))
        if self.auto_ack:
            self.delivered = [entry.id for entry in entries]
        return entries, gone


class StreamConsumer(Generic[T]):
    def __init__(  # noqa: PLR0913
        self,
        redis: "Redis",
        stream: Stream[T],
        group: str,
        name: str = DEFAULT_NAME,
        *,
        start_id: str = "$",
        count: int = 100,
        block: float = 5.0,
        auto_ack: bool = False,
    ) -> None:
        self._redis = redis
        self._cursor = _Cursor(
            stream,
            group=group,
            name=name,
            start_id=start_id,
            count=count,
            block=block,
            auto_ack=auto_ack,
        )

    def create_group(self) -> None:
        cursor = self._cursor
        try:
            self._redis.xgroup_create(
                cursor.stream.key,
                cursor.group,
                id=cursor.start_id,
                mkstream=True,
            )
        except ResponseError as exc:
            if not _group_exists(exc):
                raise
        cursor.group_ready = True

    def read(self) -> list[StreamEntry[T]]:
        if not self._cursor.group_ready:
            self.create_group()

        self._ack_delivered()

        while True:
            reply = self._redis.xreadgroup(**self._cursor.request())
            settled = self._cursor.settle(reply)
            if settled is None:
                continue
            entries, gone = settled
            if gone:
                self.ack(*gone)
            return entries

    def ack(self, *entries: StreamEntry[T] | str) -> None:
        if entries:
            cursor = self._cursor
            self._redis.xack(cursor.stream.key, cursor.group, *_ids(entries))

    def _ack_delivered(self) -> None:
        self.ack(*self._cursor.delivered)
        self._cursor.delivered = []

    def __iter__(self) -> Iterator[StreamEntry[T]]:
        while True:
            yield from self.read()


class AsyncStreamConsumer(Generic[T]):
    def __init__(  # noqa: PLR0913
        self,
        redis: "AsyncRedis",
        stream: Stream[T],
        group: str,
        name: str = DEFAULT_NAME,
        *,
        start_id: str = "$",
        count: int = 100,
        block: float = 5.0,
        auto_ack: bool = False,
    ) -> None:
        self._redis = redis
        self._cursor = _Cursor(
            stream,
            group=group,
            name=name,
            start_id=start_id,
            count=count,
            block=block,
            auto_ack=auto_ack,
        )

    async def create_group(self) -> None:
        cursor = self._cursor
        try:
            await self._redis.xgroup_create(
                cursor.stream.key,
                cursor.group,
                id=cursor.start_id,
                mkstream=True,
            )
        except ResponseError as exc:
            if not _group_exists(exc):
                raise
        cursor.group_ready = True

    async def read(self) -> list[StreamEntry[T]]:
        if not self._cursor.group_ready:
            await self.create_group()
        await self._ack_delivered()
        while True:
            reply = await self._redis.xreadgroup(**self._cursor.request())
            settled = self._cursor.settle(reply)
            if settled is None:
                continue
            entries, gone = settled
            if gone:
                await self.ack(*gone)
            return entries

    async def ack(self, *entries: StreamEntry[T] | str) -> None:
        if entries:
            cursor = self._cursor
            await self._redis.xack(
                cursor.stream.key, cursor.group, *_ids(entries)
            )

    async def _ack_delivered(self) -> None:
        await self.ack(*self._cursor.delivered)
        self._cursor.delivered = []

    async def __aiter__(self) -> AsyncIterator[StreamEntry[T]]:
        while True:
            for entry in await self.read():
                yield entry


class RedisStreams:
    def __init__(
        self, redis: "Redis", group: str, name: str = DEFAULT_NAME
    ) -> None:
        self._redis = redis
        self._group = group
        self._name = name

    def user_usage(
        self, **options: Unpack[ConsumerOptions]
    ) -> StreamConsumer[UserUsageMessage]:
        return self._consumer(USER_USAGE, options)

    def subscription_requests(
        self, **options: Unpack[ConsumerOptions]
    ) -> StreamConsumer[SubscriptionRequestMessage]:
        return self._consumer(SUBSCRIPTION_REQUESTS, options)

    def node_connections(
        self, **options: Unpack[ConsumerOptions]
    ) -> StreamConsumer[NodeConnectionsMessage]:
        return self._consumer(NODE_CONNECTIONS, options)

    def _consumer(
        self, stream: Stream[T], options: ConsumerOptions
    ) -> StreamConsumer[T]:
        return StreamConsumer(
            self._redis, stream, self._group, self._name, **options
        )


class AsyncRedisStreams:
    def __init__(
        self, redis: "AsyncRedis", group: str, name: str = DEFAULT_NAME
    ) -> None:
        self._redis = redis
        self._group = group
        self._name = name

    def user_usage(
        self, **options: Unpack[ConsumerOptions]
    ) -> AsyncStreamConsumer[UserUsageMessage]:
        return self._consumer(USER_USAGE, options)

    def subscription_requests(
        self, **options: Unpack[ConsumerOptions]
    ) -> AsyncStreamConsumer[SubscriptionRequestMessage]:
        return self._consumer(SUBSCRIPTION_REQUESTS, options)

    def node_connections(
        self, **options: Unpack[ConsumerOptions]
    ) -> AsyncStreamConsumer[NodeConnectionsMessage]:
        return self._consumer(NODE_CONNECTIONS, options)

    def _consumer(
        self, stream: Stream[T], options: ConsumerOptions
    ) -> AsyncStreamConsumer[T]:
        return AsyncStreamConsumer(
            self._redis, stream, self._group, self._name, **options
        )


def _entries(reply: object) -> list[RawEntry]:
    # redis-py shapes the reply by protocol and version: RESP2 gives
    # [[key, entries]], RESP3 {key: [entries]}, the unified form {key: entries}.
    # Only one stream is read, so the first one is the only one.
    if not reply:
        return []
    if isinstance(reply, dict):
        entries: list[Any] = next(iter(reply.values()))
        if entries and isinstance(entries[0], list):
            entries = entries[0]
        return entries
    first: list[Any] = reply[0]  # type: ignore[index]
    return list(first[1])


def _ids(entries: tuple[StreamEntry[Any] | str, ...]) -> list[str]:
    return [e.id if isinstance(e, StreamEntry) else e for e in entries]


def _group_exists(exc: ResponseError) -> bool:
    return str(exc).startswith("BUSYGROUP")


def _text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value
