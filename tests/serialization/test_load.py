from datetime import UTC, datetime

from remnawave.serialization import AdaptixSerializer
from tests.samples import Box, Sample


def test_camel_to_snake(serializer: AdaptixSerializer, payload: bytes) -> None:
    loaded = serializer.load(payload, Sample)

    assert loaded.short_uuid == "kR3nQ"
    assert loaded.nested.used_bytes == 10


def test_datetime(serializer: AdaptixSerializer, payload: bytes) -> None:
    loaded = serializer.load(payload, Sample)

    assert loaded.created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_null_is_none(serializer: AdaptixSerializer, payload: bytes) -> None:
    loaded = serializer.load(payload, Sample)

    assert loaded.nested.online_at is None


def test_list(serializer: AdaptixSerializer, payload: bytes) -> None:
    loaded = serializer.load(b"[" + payload + b"]", list[Sample])

    assert len(loaded) == 1
    assert loaded[0].short_uuid == "kR3nQ"


def test_generic(serializer: AdaptixSerializer, payload: bytes) -> None:
    loaded = serializer.load(b'{"response":' + payload + b"}", Box[Sample])

    assert loaded.response.short_uuid == "kR3nQ"
