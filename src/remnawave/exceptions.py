class RemnawaveError(Exception):
    pass


class TransportError(RemnawaveError):
    pass


class NetworkError(TransportError):
    pass


class RequestTimeoutError(TransportError):
    pass


class SerializationError(RemnawaveError):
    pass


class ApiError(RemnawaveError):
    def __init__(
        self,
        message: str,
        status: int,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.error_code = error_code

    def __str__(self) -> str:
        code = f" [{self.error_code}]" if self.error_code else ""
        return f"HTTP {self.status}{code}: {self.message}"


class BadRequestError(ApiError):
    pass


class UnauthorizedError(ApiError):
    pass


class ForbiddenError(ApiError):
    pass


class NotFoundError(ApiError):
    pass


class ConflictError(ApiError):
    pass


class TooManyRequestsError(ApiError):
    pass


class ServerError(ApiError):
    pass


class WebhookSignatureError(RemnawaveError):
    pass
