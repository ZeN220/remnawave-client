import json
from collections.abc import Mapping
from typing import Generic, TypeVar

from adaptix import Chain, P, Retort, loader, name_mapping
from adaptix.load_error import LoadError

from remnawave.exceptions import SerializationError
from remnawave.serialization import build_default_retort
from remnawave.streams.messages import (
    NodeConnectionsMessage,
    SubscriptionRequestMessage,
    UserUsageMessage,
)

T = TypeVar("T")

RawFields = Mapping[str, str] | Mapping[bytes, bytes]

KEY_PREFIX = "ioraw:"
MESSAGE_VERSION = "1"


def _user_usage_records(raw: str) -> list[dict[str, str]]:
    # "userId:totalBytes" pairs separated by ";"
    return [
        dict(zip(("userId", "totalBytes"), pair.split(":"), strict=True))
        for pair in raw.split(";")
    ]


# Every value in a stream entry is a string: ids and byte counters are
# bigints written as decimals, nested structures are packed into one field.
RETORT = build_default_retort(
    loader(int, int),
    name_mapping(UserUsageMessage, map={"timestamp": "ts"}),
    name_mapping(NodeConnectionsMessage, map={"timestamp": "ts"}),
    loader(P[UserUsageMessage].records, _user_usage_records, Chain.FIRST),
    loader(P[NodeConnectionsMessage].users, json.loads, Chain.FIRST),
)


class Stream(Generic[T]):
    def __init__(
        self,
        key: str,
        message_type: type[T],
        retort: Retort = RETORT,
    ) -> None:
        self.key = key
        self.message_type = message_type
        self._retort = retort

    def parse(self, fields: RawFields) -> T:
        decoded = {_text(name): _text(value) for name, value in fields.items()}
        version = decoded.get("v")
        if version != MESSAGE_VERSION:
            message = f"unsupported {self.key} message version: {version!r}"
            raise SerializationError(message)
        try:
            loaded: T = self._retort.load(decoded, self.message_type)
        except (LoadError, ValueError) as exc:
            raise SerializationError(str(exc)) from exc
        return loaded


def _text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value


USER_USAGE = Stream(f"{KEY_PREFIX}export:user_usage", UserUsageMessage)
SUBSCRIPTION_REQUESTS = Stream(
    f"{KEY_PREFIX}export:subscription_requests",
    SubscriptionRequestMessage,
)
NODE_CONNECTIONS = Stream(
    f"{KEY_PREFIX}export:node_connections",
    NodeConnectionsMessage,
)
