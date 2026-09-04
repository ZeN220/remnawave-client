import pytest
from adaptix.load_error import LoadError

from remnawave.exceptions import SerializationError
from remnawave.serialization import AdaptixSerializer
from tests.samples import Sample


def test_broken_json(serializer: AdaptixSerializer) -> None:
    with pytest.raises(SerializationError) as info:
        serializer.load(b"{not json", Sample)

    assert isinstance(info.value.__cause__, ValueError)


def test_empty_body(serializer: AdaptixSerializer) -> None:
    with pytest.raises(SerializationError):
        serializer.load(b"", Sample)


def test_missing_field(serializer: AdaptixSerializer) -> None:
    with pytest.raises(SerializationError) as info:
        serializer.load(b'{"id":1}', Sample)

    assert isinstance(info.value.__cause__, LoadError)


def test_wrong_type(serializer: AdaptixSerializer, payload: bytes) -> None:
    broken = payload.replace(b'"id":1', b'"id":"one"')

    with pytest.raises(SerializationError) as info:
        serializer.load(broken, Sample)

    assert isinstance(info.value.__cause__, LoadError)


def test_unserializable(serializer: AdaptixSerializer) -> None:
    with pytest.raises(SerializationError):
        serializer.dump(object())
