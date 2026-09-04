import pytest

from remnawave.operations import RequestBuilder, ResponseParser
from remnawave.serialization import AdaptixSerializer


@pytest.fixture
def base_url() -> str:
    return "https://panel.example.com"


@pytest.fixture
def serializer() -> AdaptixSerializer:
    return AdaptixSerializer()


@pytest.fixture
def builder(base_url: str, serializer: AdaptixSerializer) -> RequestBuilder:
    return RequestBuilder(base_url, serializer)


@pytest.fixture
def parser(serializer: AdaptixSerializer) -> ResponseParser:
    return ResponseParser(serializer)
