from dataclasses import dataclass
from typing import Any, Generic, TypeVar, overload

from remnawave.exceptions import (
    ApiError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    SerializationError,
    ServerError,
    TooManyRequestsError,
    UnauthorizedError,
)
from remnawave.http import Response
from remnawave.serialization import Serializer

from .operation import (
    AnyOperation,
    NoContentOperation,
    Operation,
    RawOperation,
)

T = TypeVar("T")

BY_STATUS: dict[int, type[ApiError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    429: TooManyRequestsError,
}

ERROR_STATUS = 400
SERVER_ERROR_STATUS = 500


@dataclass(frozen=True, slots=True)
class _Envelope(Generic[T]):
    response: T


@dataclass(frozen=True, slots=True)
class ErrorBody:
    message: str | None = None
    error_code: str | None = None


class ResponseParser:
    def __init__(self, serializer: Serializer) -> None:
        self._serializer = serializer

    @overload
    def parse(
        self,
        operation: NoContentOperation,
        response: Response,
    ) -> None: ...

    @overload
    def parse(self, operation: RawOperation, response: Response) -> bytes: ...

    @overload
    def parse(self, operation: "Operation[T]", response: Response) -> T: ...

    def parse(self, operation: AnyOperation, response: Response) -> Any:
        if response.status >= ERROR_STATUS:
            raise self._error(response)

        if isinstance(operation, NoContentOperation):
            return None

        if isinstance(operation, RawOperation):
            return response.content

        envelope = self._serializer.load(
            response.content,
            _envelope_of(operation.returns),
        )
        return envelope.response

    def _error(self, response: Response) -> ApiError:
        body = self._error_body(response)
        error = _by_status(response.status)
        message = body.message or "request failed"
        return error(message, response.status, body.error_code)

    def _error_body(self, response: Response) -> ErrorBody:
        try:
            return self._serializer.load(response.content, ErrorBody)
        except SerializationError:
            return ErrorBody()


def _envelope_of(returns: type[T]) -> type[_Envelope[T]]:
    return _Envelope[returns]  # type: ignore[valid-type]


def _by_status(status: int) -> type[ApiError]:
    if status >= SERVER_ERROR_STATUS:
        return ServerError
    return BY_STATUS.get(status, ApiError)
