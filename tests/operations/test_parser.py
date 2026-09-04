from remnawave.http import Response
from remnawave.operations import (
    NoContentOperation,
    Operation,
    RawOperation,
    ResponseParser,
)
from tests.samples import Sample


def test_response_is_unwrapped(
    parser: ResponseParser,
    payload: bytes,
) -> None:
    operation: Operation[Sample] = Operation("GET", "/api/users", Sample)
    response = Response(status=200, content=b'{"response":' + payload + b"}")

    loaded = parser.parse(operation, response)

    assert loaded.short_uuid == "kR3nQ"


def test_list_return(parser: ResponseParser, payload: bytes) -> None:
    operation: Operation[list[Sample]] = Operation(
        "GET",
        "/api/users",
        list[Sample],
    )
    response = Response(status=200, content=b'{"response":[' + payload + b"]}")

    loaded = parser.parse(operation, response)

    assert len(loaded) == 1
    assert loaded[0].short_uuid == "kR3nQ"


def test_no_content(parser: ResponseParser) -> None:
    operation = NoContentOperation("DELETE", "/api/users/{uuid}")
    response = Response(status=204)

    assert parser.parse(operation, response) is None


def test_raw_body_is_returned_as_is(parser: ResponseParser) -> None:
    operation = RawOperation("GET", "/api/sub/{shortUuid}")
    config = b"proxies:\n  - name: node\n"
    response = Response(status=200, content=config)

    assert parser.parse(operation, response) == config
