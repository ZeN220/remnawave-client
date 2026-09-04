import json
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID

import pytest

from remnawave.operations import Operation, RawOperation, RequestBuilder
from remnawave.serialization import AdaptixSerializer
from tests.samples import Sample


class Colour(StrEnum):
    RED = "RED"


def test_method_and_url(builder: RequestBuilder, base_url: str) -> None:
    operation: Operation[Sample] = Operation(
        "GET",
        "/api/users/{uuid}",
        Sample,
    )

    request = builder.build(operation, path={"uuid": "abc"})

    assert request.method == "GET"
    assert request.url == f"{base_url}/api/users/abc"


def test_path_is_encoded(builder: RequestBuilder, base_url: str) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/u/{name}", Sample)

    request = builder.build(operation, path={"name": "john doe/../admin"})

    assert request.url == f"{base_url}/api/u/john%20doe%2F..%2Fadmin"


def test_missing_path_param(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/u/{name}", Sample)

    with pytest.raises(KeyError):
        builder.build(operation)


def test_query_drops_none(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)

    request = builder.build(operation, query={"start": 0, "tag": None})

    assert request.params == {"start": 0}


def test_body_is_serialized(builder: RequestBuilder, sample: Sample) -> None:
    operation: Operation[Sample] = Operation("POST", "/api/users", Sample)

    request = builder.build(operation, body=sample)

    assert request.headers["Content-Type"] == "application/json"
    assert request.content is not None
    assert json.loads(request.content)["shortUuid"] == "kR3nQ"


def test_no_body(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)

    request = builder.build(operation)

    assert request.content is None
    assert "Content-Type" not in request.headers
    assert request.headers["Accept"] == "application/json"


def test_trailing_slash_in_base_url(serializer: AdaptixSerializer) -> None:
    builder = RequestBuilder("https://panel.example.com/", serializer)
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)

    request = builder.build(operation)

    assert request.url == "https://panel.example.com/api/users"


def test_raw_operation_does_not_ask_for_json(builder: RequestBuilder) -> None:
    operation = RawOperation("GET", "/api/sub/{shortUuid}")

    request = builder.build(operation, path={"shortUuid": "kR3nQ"})

    assert "Accept" not in request.headers


def test_datetime_query_is_iso_with_zone(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/stats", Sample)
    moment = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    request = builder.build(operation, query={"start": moment})

    assert request.params == {"start": "2026-01-01T12:00:00+00:00"}


def test_naive_datetime_query_gets_utc(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/stats", Sample)
    naive = datetime(2026, 1, 1, 12, 0)  # noqa: DTZ001

    request = builder.build(operation, query={"start": naive})

    assert request.params == {"start": "2026-01-01T12:00:00+00:00"}


def test_date_and_uuid_query(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/stats", Sample)
    uuid = UUID("11111111-1111-4111-8111-111111111111")

    query = {"day": date(2026, 1, 1), "id": uuid}
    request = builder.build(operation, query=query)

    assert request.params == {"day": "2026-01-01", "id": str(uuid)}


def test_enum_query_uses_value(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)

    request = builder.build(operation, query={"status": Colour.RED})

    assert request.params == {"status": "RED"}


def test_complex_query_is_rejected(builder: RequestBuilder) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)

    with pytest.raises(ValueError, match="wire format"):
        builder.build(operation, query={"filters": [{"id": "a"}]})
