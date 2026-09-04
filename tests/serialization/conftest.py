import pytest

from remnawave.serialization import AdaptixSerializer


@pytest.fixture
def serializer() -> AdaptixSerializer:
    return AdaptixSerializer()
