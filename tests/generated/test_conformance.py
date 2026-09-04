import importlib
import pkgutil
from typing import Any

import pytest

from remnawave._generated import methods
from remnawave._generated.renames import NAME_MAPPING
from remnawave.http import Response
from remnawave.operations import (
    AnyOperation,
    NoContentOperation,
    Operation,
    RawOperation,
    ResponseParser,
)
from remnawave.serialization import AdaptixSerializer, build_default_retort
from tests.generated.examples import example_for, operations


def _generated() -> list[tuple[str, AnyOperation]]:
    found = []
    for info in pkgutil.iter_modules(methods.__path__):
        module = importlib.import_module(f"{methods.__name__}.{info.name}")
        for name, value in vars(module).items():
            if isinstance(value, Operation | NoContentOperation | RawOperation):
                found.append((f"{info.name}.{name}", value))
    return found


GENERATED = _generated()
BY_ROUTE = {(http, path): schema for http, path, schema in operations()}


@pytest.fixture(scope="module")
def parser() -> ResponseParser:
    retort = build_default_retort(*NAME_MAPPING)
    return ResponseParser(AdaptixSerializer(retort))


def test_every_spec_operation_is_generated() -> None:
    routes = {(op.method, op.path) for _, op in GENERATED}

    assert routes == set(BY_ROUTE)


@pytest.mark.parametrize(
    ("name", "operation"),
    GENERATED,
    ids=[name for name, _ in GENERATED],
)
def test_response_loads(
    parser: ResponseParser,
    name: str,
    operation: AnyOperation,
) -> None:
    schema: dict[str, Any] | None = BY_ROUTE[(operation.method, operation.path)]

    if isinstance(operation, NoContentOperation):
        assert schema is None
        assert parser.parse(operation, Response(status=204)) is None
        return

    if isinstance(operation, RawOperation):
        response = Response(status=200, content=b"raw")
        assert parser.parse(operation, response) == b"raw"
        return

    assert schema is not None, f"{name}: спека обещает тело, генератор — нет"
    response = Response(status=200, content=example_for(schema))

    parser.parse(operation, response)
