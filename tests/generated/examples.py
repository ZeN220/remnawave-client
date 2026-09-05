import json
from pathlib import Path
from typing import Any

from tools.codegen.parse import date_type
from tools.codegen.specs import newest

# От файла, а не от рабочего каталога: pytest могут запустить откуда угодно.
# Версия не прибита: после обновления спеки тесты поедут за ней.
SPECS = Path(__file__).resolve().parents[2] / "specs"
MAX_DEPTH = 12

_spec: dict[str, Any] | None = None


def spec() -> dict[str, Any]:
    global _spec  # noqa: PLW0603
    if _spec is None:
        _spec = json.loads(newest(SPECS).read_text(encoding="utf-8"))
    return _spec


def schemas() -> dict[str, Any]:
    found: dict[str, Any] = spec()["components"]["schemas"]
    return found


def operations() -> list[tuple[str, str, dict[str, Any] | None]]:
    found = []
    for path, item in spec()["paths"].items():
        for http, operation in item.items():
            if not isinstance(operation, dict):
                continue
            if "operationId" not in operation:
                continue
            found.append((http.upper(), path, _success(operation)))
    return found


def example_body(dto: str) -> bytes:
    return json.dumps(_example(schemas()[dto], 0)).encode()


def example_for(schema: dict[str, Any]) -> bytes:
    return json.dumps(_example(schema, 0)).encode()


def _success(operation: dict[str, Any]) -> dict[str, Any] | None:
    codes = sorted(c for c in operation["responses"] if c.startswith("2"))
    content = operation["responses"][codes[0]].get("content")
    if not content:
        return None
    schema: dict[str, Any] = content["application/json"]["schema"]
    return schema


def _example(schema: dict[str, Any], depth: int) -> Any:  # noqa: ANN401, PLR0911
    if depth > MAX_DEPTH:
        return None
    schema = _deref(schema)

    if "allOf" in schema:
        merged: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        for part in schema["allOf"]:
            resolved = _deref(part)
            merged["properties"].update(resolved.get("properties") or {})
            merged["required"].extend(resolved.get("required") or ())
        return _example(merged, depth)

    if "enum" in schema:
        return next((v for v in schema["enum"] if v is not None), None)

    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props: dict[str, Any] = schema.get("properties") or {}
        return {name: _example(sub, depth + 1) for name, sub in props.items()}
    if kind == "array":
        return [_example(schema.get("items") or {}, depth + 1)]
    if kind == "boolean":
        return True
    if kind in {"number", "integer"}:
        return 1
    return _string(schema)


def _string(schema: dict[str, Any]) -> str:
    fmt = schema.get("format")
    if fmt == "uuid":
        return "11111111-1111-4111-8111-111111111111"
    if fmt in {"date-time", "date"}:
        return "2026-01-01T00:00:00.000Z"
    if fmt == "email":
        return "user@example.com"
    dated = date_type(schema.get("pattern"))
    if dated == "datetime":
        return "2026-01-01T00:00:00.000Z"
    if dated == "date":
        return "2026-01-01"
    return "value"


def _deref(schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        schema = schemas()[schema["$ref"].rsplit("/", 1)[-1]]
    return schema
