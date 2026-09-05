import re
from collections.abc import Iterable
from typing import Any

from .ir import (
    Api,
    Enum,
    Field,
    Group,
    Method,
    Model,
    Pagination,
    Param,
    Webhook,
)
from .naming import camel, enum_member, pascal, singular, snake
from .overlay import Overlay

PRIMITIVES: dict[tuple[str | None, str | None], str] = {
    ("string", None): "str",
    ("string", "uuid"): "UUID",
    ("string", "date-time"): "datetime",
    ("string", "date"): "date",
    (None, "date"): "date",
    (None, "date-time"): "datetime",
    ("string", "email"): "str",
    ("string", "ipv4"): "str",
    ("string", "ipv6"): "str",
    ("string", "uri"): "str",
    ("string", "binary"): "bytes",
    ("boolean", None): "bool",
    ("integer", None): "int",
    ("number", None): "int",
}

# Панель описывает даты регуляркой и не всегда сопровождает её форматом:
# в 3.4.3 у двух десятков полей format: date-time просто пропал. Разбирать
# текст регулярки хрупко, поэтому спрашиваем её саму — что она принимает.
_DATETIME_SAMPLES = ("2024-01-15T10:30:00Z", "2000-02-29T23:59:59.123Z")
_DATE_SAMPLES = ("2024-01-15", "2000-02-29", "1999-12-31")
# Без отбраковки в дату попал бы любой паттерн вида ^[A-Za-z0-9-]+$.
_NOT_DATE_SAMPLES = (
    "2024-13-01",
    "2024-01-32",
    "2024-02-30",
    "20240115",
    "abc",
)


def date_type(pattern: str | None) -> str | None:
    """datetime, date или ничего — по тому, что регулярка принимает."""
    if not pattern:
        return None
    try:
        matcher = re.compile(pattern)
    except re.error:
        return None
    if all(matcher.search(sample) for sample in _DATETIME_SAMPLES):
        return "datetime"
    if all(matcher.search(sample) for sample in _DATE_SAMPLES) and not any(
        matcher.search(sample) for sample in _NOT_DATE_SAMPLES
    ):
        return "date"
    return None


def _primitive(schema: dict[str, Any]) -> str | None:
    """Скаляр по типу и формату, а без формата — по регулярке."""
    fmt = schema.get("format")
    if fmt is None:
        dated = date_type(schema.get("pattern"))
        if dated is not None:
            return dated
    return PRIMITIVES.get((schema.get("type"), fmt))


Names = dict[str, str]
Models = tuple[Model, ...]
Enums = tuple[Enum, ...]

_ACTIONS = (
    "GetAll",
    "Get",
    "CreateMany",
    "Create",
    "Update",
    "Delete",
    "Remove",
    "Reorder",
    "Revoke",
    "Extend",
    "Reset",
    "Enable",
    "Disable",
    "Add",
    "Set",
    "Resolve",
    "Generate",
    "Restart",
    "Debug",
    "Bulk",
)

_PAGE_FIELDS = 2
_DEFAULT_PAGE_SIZE = 100

MARKER = re.compile(r"#([me])(\d+)#")


class Builder:
    def __init__(self, spec: dict[str, Any], overlay: Overlay) -> None:
        self._spec = spec
        self._schemas: dict[str, Any] = spec["components"]["schemas"]
        self._overlay = overlay
        self._model_shapes: dict[tuple[Any, ...], int] = {}
        self._model_fields: dict[int, tuple[Field, ...]] = {}
        self._model_names: dict[int, set[str]] = {}
        self._enum_shapes: dict[tuple[str, ...], int] = {}
        self._enum_names: dict[int, set[str]] = {}
        self.unsupported: list[str] = []

    def build(self) -> Api:
        groups = self._groups()
        hooks = self._webhooks()
        models, enums, names = self._named()
        return Api(
            version=self._spec["info"]["version"],
            enums=enums,
            models=models,
            groups=tuple(_resolve_group(g, names) for g in groups),
            webhooks=tuple(
                Webhook(
                    scope=w.scope,
                    type_name=_substitute(w.type_name, names),
                )
                for w in hooks
            ),
            renames=self._renames(models),
        )

    def _webhooks(self) -> list[Webhook]:
        """События вебхуков описаны в components, но ни одна операция на них
        не ссылается — обход от операций их не достаёт."""
        found = []
        for name, schema in sorted(self._schemas.items()):
            match = re.fullmatch(r"RemnawaveWebhook(\w+)EventsDto", name)
            if match is None:
                continue
            scope = schema["properties"]["scope"]["enum"][0]
            hint = f"{pascal(match.group(1))}Event"
            resolved = self._type(schema, hint, body=False)
            found.append(Webhook(scope=scope, type_name=resolved))
        return found

    def _type(  # noqa: PLR0911
        self,
        schema: dict[str, Any],
        hint: str,
        *,
        body: bool,
    ) -> str:
        schema = self._deref(schema)

        if "enum" in schema and schema.get("type") == "string":
            return self._enum(schema, hint)

        if "allOf" in schema:
            merged = _merge(map(self._deref, schema["allOf"]))
            return self._object(merged, hint, body=body)

        variants = schema.get("oneOf") or schema.get("anyOf")
        if variants:
            return self._variants(variants, hint)

        kind = schema.get("type")
        if kind == "array":
            items = schema.get("items") or {}
            inner = self._type(items, singular(hint), body=body)
            return f"list[{inner}]"
        if kind == "object" or "properties" in schema:
            return self._object(schema, hint, body=body)

        primitive = _primitive(schema)
        if primitive is not None:
            return primitive
        if kind == "number":
            return "int"
        return "Any"

    def _variants(self, variants: list[dict[str, Any]], hint: str) -> str:
        scalars = {_primitive(v) for v in map(self._deref, variants)}
        if len(scalars) == 1 and None not in scalars:
            return scalars.pop() or "Any"
        self.unsupported.append(hint)
        return "Any"

    def _object(self, schema: dict[str, Any], hint: str, *, body: bool) -> str:
        props: dict[str, Any] = schema.get("properties") or {}
        if not props:
            return "dict[str, Any]"

        required = set(schema.get("required") or ())
        fields = []
        for wire, sub in props.items():
            name = self._overlay.field_names.get(wire) or snake(wire)
            child = f"{hint}{pascal(singular(wire))}"
            resolved = self._type(sub, child, body=body)
            forced = self._overlay.field_types.get(wire)
            if forced:
                resolved = forced
            optional = wire not in required
            annotation = _optional(
                resolved,
                self._deref(sub),
                required=not optional,
                body=body,
            )
            fields.append(
                Field(
                    name=name,
                    type=annotation,
                    wire=wire,
                    default=_default(optional=optional, body=body),
                ),
            )

        key = tuple((f.name, f.type, f.wire, f.default) for f in fields)
        shape = self._model_shapes.setdefault(key, len(self._model_shapes))
        self._model_fields[shape] = tuple(fields)
        self._model_names.setdefault(shape, set()).add(hint)
        return f"#m{shape}#"

    def _enum(self, schema: dict[str, Any], hint: str) -> str:
        values = tuple(v for v in schema["enum"] if v is not None)
        if len(values) == 1:
            # Одно значение — это константа-дискриминатор, а не перечисление.
            # Literal вдобавок позволяет сузить union по нему.
            return f'Literal["{values[0]}"]'

        shape = self._enum_shapes.setdefault(values, len(self._enum_shapes))
        self._enum_names.setdefault(shape, set()).add(hint)
        return f"#e{shape}#"

    def _deref(self, schema: dict[str, Any]) -> dict[str, Any]:
        while "$ref" in schema:
            schema = self._schemas[schema["$ref"].rsplit("/", 1)[-1]]
        return schema

    def _named(self) -> tuple[Models, Enums, Names]:
        names: dict[str, str] = {}
        taken: set[str] = set()

        enums = []
        for shape, candidates in sorted(self._enum_names.items()):
            auto = _unique(min(sorted(candidates), key=len), taken)
            name = self._overlay.types.get(auto, auto)
            names[f"#e{shape}#"] = name
            values = next(v for v, s in self._enum_shapes.items() if s == shape)
            members = tuple((enum_member(v), v) for v in values)
            enums.append(Enum(name=name, members=members))

        for shape, candidates in sorted(self._model_names.items()):
            auto = _unique(min(sorted(candidates), key=len), taken)
            names[f"#m{shape}#"] = self._overlay.types.get(auto, auto)

        models = []
        for shape, fields in sorted(self._model_fields.items()):
            name = names[f"#m{shape}#"]
            secret = set(self._overlay.secret_fields.get(name) or ())
            models.append(
                Model(
                    name=name,
                    fields=tuple(
                        Field(
                            name=f.name,
                            type=_substitute(f.type, names),
                            wire=f.wire,
                            default=f.default,
                            secret=f.wire in secret,
                        )
                        for f in fields
                    ),
                ),
            )
        return tuple(models), tuple(enums), names

    def _renames(self, models: tuple[Model, ...]) -> dict[str, dict[str, str]]:
        renames: dict[str, dict[str, str]] = {}
        for model in models:
            odd = {
                f.name: f.wire for f in model.fields if camel(f.name) != f.wire
            }
            if odd:
                renames[model.name] = odd
        return renames

    def _groups(self) -> list[Group]:
        collected: dict[str, list[Method]] = {}
        docs: dict[str, str] = {}
        for path, item in self._spec["paths"].items():
            for http, op in item.items():
                if not isinstance(op, dict) or "operationId" not in op:
                    continue
                tag = op["tags"][0]
                group = self._overlay.groups.get(tag) or snake(_clean_tag(tag))
                docs[group] = tag
                method = self._method(path, http.upper(), op)
                collected.setdefault(group, []).append(method)
        return [
            Group(
                name=name,
                class_name=f"{pascal(name)}Api",
                doc=docs[name],
                methods=tuple(methods),
            )
            for name, methods in sorted(collected.items())
        ]

    def _method(self, path: str, http: str, op: dict[str, Any]) -> Method:
        operation_id: str = op["operationId"]
        name = self._overlay.methods.get(operation_id)
        if name is None:
            name = snake(operation_id.split("_", 1)[1])

        raw_params = op.get("parameters") or []
        params = [self._param(p, operation_id) for p in raw_params]
        status, schema = self._success(op)
        returns = None
        kind = "typed"
        if schema is None:
            kind = "raw" if status == "200" else "no_content"
        else:
            hint = _entity(re.sub(r"ResponseDto$", "", schema["name"]))
            returns = self._type(schema["inner"], pascal(hint), body=False)

        query = tuple(p for p, place in params if place == "query")
        pagination = None
        if schema is not None:
            pagination = self._pagination(schema["inner"], query, op)

        return Method(
            name=name,
            http=http,
            path=path,
            kind=kind,
            returns=returns,
            pagination=pagination,
            body=self._body(op, operation_id),
            doc=op.get("summary"),
            path_params=tuple(p for p, place in params if place == "path"),
            query_params=query,
        )

    def _pagination(
        self,
        inner: dict[str, Any],
        query: tuple[Param, ...],
        op: dict[str, Any],
    ) -> Pagination | None:
        """Листинг узнаётся по форме: start/size в query и {total, <массив>}."""
        names = {p.name for p in query}
        if not {"start", "size"} <= names:
            return None

        props: dict[str, Any] = inner.get("properties") or {}
        arrays = [k for k, v in props.items() if v.get("type") == "array"]
        shaped = len(props) == _PAGE_FIELDS and len(arrays) == 1
        if not shaped or "total" not in props:
            return None

        items = arrays[0]
        item_type = self._type(
            props[items].get("items") or {},
            singular(pascal(items)),
            body=False,
        )
        return Pagination(
            items_field=snake(items),
            item_type=item_type,
            max_page_size=_max_size(op),
        )

    def _param(self, raw: dict[str, Any], hint: str) -> tuple[Param, str]:
        wire = raw["name"]
        param = Param(
            name=snake(wire),
            wire=wire,
            type=self._type(raw.get("schema") or {}, pascal(hint), body=False),
            required=bool(raw.get("required")),
        )
        return param, raw["in"]

    def _success(self, op: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        codes = sorted(c for c in op["responses"] if c.startswith("2"))
        # В 2.x часть операций не объявляет 2xx вовсе: успешный ответ лежит
        # под default рядом с ошибками.
        status = codes[0] if codes else "200"
        response = op["responses"].get(status) or op["responses"].get("default")
        if response is None:
            return status, None
        content = response.get("content")
        if not content:
            return status, None
        raw = content["application/json"]["schema"]
        name = raw.get("$ref", "").rsplit("/", 1)[-1] or "Response"
        body = self._deref(raw)
        inner = (body.get("properties") or {}).get("response")
        return status, {
            "name": name,
            "inner": body if inner is None else inner,
        }

    def _body(self, op: dict[str, Any], hint: str) -> str | None:
        request = op.get("requestBody")
        if not request:
            return None
        raw = request["content"]["application/json"]["schema"]
        name = raw.get("$ref", "").rsplit("/", 1)[-1] or f"{hint}Body"
        return self._type(raw, pascal(re.sub(r"Dto$", "", name)), body=True)


def _optional(
    resolved: str,
    schema: dict[str, Any],
    *,
    required: bool,
    body: bool,
) -> str:
    if schema.get("nullable") and resolved != "Any":
        # Any и так допускает None: лишнее объединение только плодит
        # ложные различия между одинаковыми по сути формами.
        resolved = f"{resolved} | None"
    if required:
        return resolved
    return f"Omittable[{resolved}]" if body else f"{resolved} | None"


def _merge(parts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for part in parts:
        properties.update(part.get("properties") or {})
        required.extend(part.get("required") or ())
    return {"type": "object", "properties": properties, "required": required}


def _entity(name: str) -> str:
    for action in _ACTIONS:
        if name.startswith(action) and len(name) > len(action):
            rest = name[len(action) :]
            if rest[0].isupper():
                return rest
    return name


def _max_size(op: dict[str, Any]) -> int:
    for param in op.get("parameters") or []:
        if param["name"] == "size":
            maximum = (param.get("schema") or {}).get("maximum")
            if isinstance(maximum, int):
                return maximum
    return _DEFAULT_PAGE_SIZE


def _default(*, optional: bool, body: bool) -> str | None:
    if not optional:
        return None
    return "Omitted()" if body else "None"


def _clean_tag(tag: str) -> str:
    without_brackets = re.sub(r"[\[\]]", " ", tag)
    return re.sub(r"\s*Controller$", "", without_brackets).strip()


def _unique(name: str, taken: set[str]) -> str:
    candidate = name or "Unnamed"
    index = 2
    while candidate in taken:
        candidate = f"{name}{index}"
        index += 1
    taken.add(candidate)
    return candidate


def _substitute(value: str, names: dict[str, str]) -> str:
    return MARKER.sub(lambda m: names[m.group(0)], value)


def _resolve_pagination(
    pagination: Pagination | None,
    names: dict[str, str],
) -> Pagination | None:
    if pagination is None:
        return None
    return Pagination(
        items_field=pagination.items_field,
        item_type=_substitute(pagination.item_type, names),
        max_page_size=pagination.max_page_size,
    )


def _resolve_params(
    params: tuple[Param, ...],
    names: dict[str, str],
) -> tuple[Param, ...]:
    return tuple(
        Param(
            name=p.name,
            wire=p.wire,
            type=_substitute(p.type, names),
            required=p.required,
        )
        for p in params
    )


def _resolve_group(group: Group, names: dict[str, str]) -> Group:
    return Group(
        name=group.name,
        class_name=group.class_name,
        doc=group.doc,
        methods=tuple(
            Method(
                name=m.name,
                http=m.http,
                path=m.path,
                kind=m.kind,
                returns=_substitute(m.returns, names) if m.returns else None,
                body=_substitute(m.body, names) if m.body else None,
                doc=m.doc,
                path_params=_resolve_params(m.path_params, names),
                query_params=_resolve_params(m.query_params, names),
                pagination=_resolve_pagination(m.pagination, names),
            )
            for m in group.methods
        ),
    )
