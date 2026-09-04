import json

import pytest

from remnawave.exceptions import SerializationError
from remnawave.serialization import AdaptixSerializer
from tests.samples import Box, Sample


def test_snake_to_camel(serializer: AdaptixSerializer, sample: Sample) -> None:
    dumped = json.loads(serializer.dump(sample))

    assert dumped["shortUuid"] == "kR3nQ"
    assert dumped["nested"]["usedBytes"] == 10


def test_datetime(serializer: AdaptixSerializer, sample: Sample) -> None:
    dumped = json.loads(serializer.dump(sample))

    assert dumped["createdAt"] == "2026-01-01T00:00:00+00:00"


def test_roundtrip(serializer: AdaptixSerializer, sample: Sample) -> None:
    assert serializer.load(serializer.dump(sample), Sample) == sample


def test_generic_needs_explicit_type(
    serializer: AdaptixSerializer,
    sample: Sample,
) -> None:
    with pytest.raises(SerializationError):
        serializer.dump(Box(response=sample))


def test_generic_with_explicit_type(
    serializer: AdaptixSerializer,
    sample: Sample,
) -> None:
    dumped = json.loads(serializer.dump(Box(response=sample), Box[Sample]))

    assert dumped["response"]["shortUuid"] == "kR3nQ"
