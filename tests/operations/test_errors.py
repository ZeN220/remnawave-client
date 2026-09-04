import pytest

from remnawave.exceptions import (
    ApiError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    ServerError,
)
from remnawave.http import Response
from remnawave.operations import Operation, ResponseParser
from tests.samples import Sample

OPERATION: Operation[Sample] = Operation("GET", "/api/users/{uuid}", Sample)


def error_response(status: int, body: bytes = b"") -> Response:
    return Response(status=status, content=body)


def test_not_found(parser: ResponseParser) -> None:
    body = (
        b'{"timestamp":"2026-01-01T00:00:00.000Z","path":"/api/users/9",'
        b'"message":"User not found","errorCode":"A025"}'
    )

    with pytest.raises(NotFoundError) as info:
        parser.parse(OPERATION, error_response(404, body))

    assert info.value.status == 404
    assert info.value.error_code == "A025"
    assert info.value.message == "User not found"
    assert str(info.value) == "HTTP 404 [A025]: User not found"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, BadRequestError),
        (404, NotFoundError),
        (409, ConflictError),
        (500, ServerError),
        (502, ServerError),
    ],
)
def test_status_mapping(
    parser: ResponseParser,
    status: int,
    expected: type[ApiError],
) -> None:
    with pytest.raises(expected):
        parser.parse(OPERATION, error_response(status, b'{"message":"boom"}'))


def test_unmapped_status(parser: ResponseParser) -> None:
    with pytest.raises(ApiError) as info:
        parser.parse(OPERATION, error_response(418, b'{"message":"teapot"}'))

    assert type(info.value) is ApiError
    assert info.value.status == 418


def test_non_json_body(parser: ResponseParser) -> None:
    with pytest.raises(ServerError) as info:
        parser.parse(OPERATION, error_response(502, b"<html>bad</html>"))

    assert info.value.message == "request failed"
    assert info.value.error_code is None


def test_empty_body(parser: ResponseParser) -> None:
    with pytest.raises(NotFoundError) as info:
        parser.parse(OPERATION, error_response(404))

    assert info.value.message == "request failed"
