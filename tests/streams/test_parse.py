import json
from datetime import UTC, datetime
from typing import Any

import pytest

from remnawave._generated.enums import SrrMatcherResponseType
from remnawave.exceptions import SerializationError
from remnawave.streams import (
    NodeConnectionIp,
    NodeConnectionUser,
    UserUsageRecord,
)
from remnawave.streams.stream import (
    NODE_CONNECTIONS,
    SUBSCRIPTION_REQUESTS,
    USER_USAGE,
    Stream,
)
from tests.streams.conftest import TS, usage

AT = datetime(2026, 9, 24, 20, tzinfo=UTC)


@pytest.mark.parametrize(
    ("stream", "key"),
    [
        (USER_USAGE, "ioraw:export:user_usage"),
        (SUBSCRIPTION_REQUESTS, "ioraw:export:subscription_requests"),
        (NODE_CONNECTIONS, "ioraw:export:node_connections"),
    ],
)
def test_key(stream: Stream[Any], key: str) -> None:
    assert stream.key == key


def test_user_usage() -> None:
    message = USER_USAGE.parse(usage("42:1024;7:18446744073709551615"))

    assert message.node_id == 3
    assert message.timestamp == AT
    assert message.records == (
        UserUsageRecord(user_id=42, total_bytes=1024),
        UserUsageRecord(user_id=7, total_bytes=18446744073709551615),
    )


def test_bytes_fields() -> None:
    raw = {k.encode(): v.encode() for k, v in usage().items()}

    assert USER_USAGE.parse(raw) == USER_USAGE.parse(usage())


def test_subscription_request() -> None:
    message = SUBSCRIPTION_REQUESTS.parse(
        {
            "v": "1",
            "userId": "42",
            "requestAt": TS,
            "srrResponseType": "XRAY_JSON",
            "userAgent": "v2rayN",
        }
    )

    assert message.user_id == 42
    assert message.request_at == AT
    assert message.srr_response_type is SrrMatcherResponseType.XRAY_JSON
    assert message.user_agent == "v2rayN"
    assert message.request_ip is None
    assert message.srr_rule_name is None


def test_node_connections() -> None:
    users = [{"userId": "42", "ips": [{"ip": "1.2.3.4", "lastSeen": TS}]}]
    message = NODE_CONNECTIONS.parse(
        {"v": "1", "nodeId": "3", "ts": TS, "users": json.dumps(users)}
    )

    assert message.node_id == 3
    assert message.users == (
        NodeConnectionUser(user_id=42, ips=(NodeConnectionIp("1.2.3.4", AT),)),
    )


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {**usage(), "v": "2"},
        usage("42:1024:1"),
        usage("42"),
        usage("x:1"),
        {**usage(), "ts": "yesterday"},
        {"v": "1", "nodeId": "3", "ts": TS},
    ],
)
def test_malformed_user_usage(fields: dict[str, str]) -> None:
    with pytest.raises(SerializationError):
        USER_USAGE.parse(fields)


def test_malformed_json() -> None:
    with pytest.raises(SerializationError):
        NODE_CONNECTIONS.parse(
            {"v": "1", "nodeId": "3", "ts": TS, "users": "{not json"}
        )
