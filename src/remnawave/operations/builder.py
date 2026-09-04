from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from urllib.parse import quote
from uuid import UUID

from remnawave.http import Request
from remnawave.serialization import Serializer

from .operation import AnyOperation, RawOperation


class RequestBuilder:
    def __init__(self, base_url: str, serializer: Serializer) -> None:
        self._base_url = base_url.rstrip("/")
        self._serializer = serializer

    def build(
        self,
        operation: AnyOperation,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: object = None,
    ) -> Request:
        headers: dict[str, str] = {}
        if not isinstance(operation, RawOperation):
            headers["Accept"] = "application/json"

        content = None
        if body is not None:
            content = self._serializer.dump(body)
            headers["Content-Type"] = "application/json"

        return Request(
            method=operation.method,
            url=self._base_url + _render_path(operation.path, path or {}),
            params=_drop_none(query or {}),
            headers=headers,
            content=content,
        )


def _render_path(template: str, values: dict[str, Any]) -> str:
    quoted = {
        key: quote(str(_wire(value)), safe="") for key, value in values.items()
    }
    return template.format_map(quoted)


def _drop_none(query: dict[str, Any]) -> dict[str, Any]:
    clean = {
        key: _wire(value) for key, value in query.items() if value is not None
    }
    for key, value in clean.items():
        if isinstance(value, dict) or (
            isinstance(value, list) and any(_is_complex(item) for item in value)
        ):
            message = (
                f"query parameter {key!r} needs a wire format "
                f"the spec does not describe"
            )
            raise ValueError(message)
    return clean


def _wire(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.isoformat()
    if isinstance(value, date | UUID):
        return str(value)
    return value


def _is_complex(value: object) -> bool:
    simple = (str, int, float, bool, UUID, date, datetime)
    return not isinstance(value, simple)
