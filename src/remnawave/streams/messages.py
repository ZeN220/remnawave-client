from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from remnawave._generated.enums import SrrMatcherResponseType

T = TypeVar("T")


@dataclass(slots=True)
class UserUsageRecord:
    user_id: int
    total_bytes: int


@dataclass(slots=True)
class UserUsageMessage:
    node_id: int
    timestamp: datetime
    records: list[UserUsageRecord]


@dataclass(slots=True)
class SubscriptionRequestMessage:
    user_id: int
    request_at: datetime
    srr_response_type: SrrMatcherResponseType
    request_ip: str | None = None
    user_agent: str | None = None
    srr_rule_name: str | None = None


@dataclass(slots=True)
class NodeConnectionIp:
    ip: str
    last_seen: datetime


@dataclass(slots=True)
class NodeConnectionUser:
    user_id: int
    ips: list[NodeConnectionIp]


@dataclass(slots=True)
class NodeConnectionsMessage:
    node_id: int
    timestamp: datetime
    users: list[NodeConnectionUser]


@dataclass(slots=True)
class StreamEntry(Generic[T]):
    id: str
    message: T
