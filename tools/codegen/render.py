"""IR на входе, файлы `_generated` на выходе.

Шаблоны намеренно тупые: сортировка полей, топологический порядок классов,
сигнатуры методов и списки импортов считаются здесь, а не в jinja.
"""

import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .ir import Api, Field, Group, Method, Model

TEMPLATES = Path(__file__).parent / "templates"
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

RETURN_BY_KIND = {"no_content": "None", "raw": "bytes"}

# Вызов в дефолте датакласса ловит RUF009; Omitted — синглтон, так что
# объявляем его константой модуля один раз.
_DEFAULTS = {"Omitted()": "OMITTED"}


@dataclass(frozen=True, slots=True)
class MethodView:
    name: str
    const: str
    http: str
    path: str
    signature: str
    returns: str
    call: str
    doc: tuple[str, ...]
    pagination: str | None
    iter_name: str | None
    item_type: str | None


@dataclass(frozen=True, slots=True)
class GroupView:
    name: str
    class_name: str
    doc: str | None
    methods: tuple[MethodView, ...]
    operations: tuple[str, ...]
    models: tuple[str, ...]
    enums: tuple[str, ...]
    stdlib: tuple[str, ...]
    paginated: bool


class Renderer:
    def __init__(self, api: Api, root: Path, package: Path) -> None:
        self._api = api
        self._root = root
        self._package = package
        self._enums = {e.name for e in api.enums}
        self._models = {m.name for m in api.models}
        self._env = Environment(
            loader=FileSystemLoader(TEMPLATES),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701 — генерируем Python, не HTML
        )
        self._env.filters["field_line"] = _field_line

    def render(self) -> None:
        self._check_names()
        self._write("__init__.py", "package.py.jinja")
        self._write("methods/__init__.py", "package.py.jinja")
        self._write("enums.py", "enums.py.jinja", enums=self._api.enums)
        self._write(
            "models.py",
            "models.py.jinja",
            models=[_sorted_fields(m) for m in _ordered(self._api.models)],
            enums=sorted(self._enums),
        )
        self._write(
            "renames.py",
            "renames.py.jinja",
            renames=self._api.renames,
        )
        self._write("groups.py", "groups.py.jinja", groups=self._api.groups)
        self._write(
            "webhooks.py",
            "webhooks.py.jinja",
            webhooks=self._api.webhooks,
        )
        self._write_types()
        for group in self._api.groups:
            self._write(
                f"methods/{group.name}.py",
                "group.py.jinja",
                group=self._view(group),
            )

    def _check_names(self) -> None:
        """Имена типов уникальны, класс группы не затеняет модель."""
        seen: set[str] = set()
        for name in [m.name for m in self._api.models] + [
            e.name for e in self._api.enums
        ]:
            if name in seen:
                message = f"имя типа {name} задано дважды"
                raise ValueError(message)
            seen.add(name)

        types = self._models | self._enums
        for group in self._api.groups:
            for name in (group.class_name, f"Async{group.class_name}"):
                if name in types:
                    message = f"имя группы {name} совпадает с типом"
                    raise ValueError(message)

    def _write_types(self) -> None:
        models = sorted(self._models)
        enums = sorted(self._enums)
        path = self._package / "types" / "__init__.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = self._env.get_template("types.py.jinja").render(
            models=models,
            enums=enums,
            names=sorted(models + enums),
        )
        path.write_text(rendered, encoding="utf-8")

    def _write(self, name: str, template: str, **context: object) -> None:
        path = self._root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = self._env.get_template(template).render(**context)
        path.write_text(rendered, encoding="utf-8")

    def _view(self, group: Group) -> GroupView:
        methods = tuple(_method_view(m) for m in group.methods)
        used: set[str] = set()
        operations: set[str] = set()
        for method in group.methods:
            operations.add(_operation_class(method))
            if method.pagination:
                operations.add("Pagination")
                used |= _references(method.pagination.item_type)
            for value in (method.returns, method.body):
                if value:
                    used |= _references(value)
            for param in method.path_params + method.query_params:
                used |= _references(param.type)

        return GroupView(
            name=group.name,
            class_name=group.class_name,
            doc=group.doc,
            methods=methods,
            operations=tuple(sorted(operations)),
            models=tuple(sorted(used & self._models)),
            enums=tuple(sorted(used & self._enums)),
            stdlib=tuple(
                sorted(used & {"UUID", "date", "datetime", "Any", "Literal"})
            ),
            paginated=any(m.pagination for m in group.methods),
        )


def _method_view(method: Method) -> MethodView:
    returns = RETURN_BY_KIND.get(method.kind) or method.returns or "None"
    return MethodView(
        name=method.name,
        const=method.name.upper(),
        http=method.http,
        path=method.path,
        signature=_signature(method),
        returns=returns,
        call=_call(method),
        doc=_doc(method.doc),
        pagination=_pagination(method),
        iter_name=_iter_name(method),
        item_type=method.pagination.item_type if method.pagination else None,
    )


def _pagination(method: Method) -> str | None:
    if method.pagination is None:
        return None
    return (
        f'pagination=Pagination(items_field="{method.pagination.items_field}", '
        f"max_page_size={method.pagination.max_page_size})"
    )


def _iter_name(method: Method) -> str | None:
    if method.pagination is None:
        return None
    if method.name.startswith("get_"):
        return f"iter_{method.name.removeprefix('get_')}"
    return f"iter_{method.name}"


def _doc(summary: str | None) -> tuple[str, ...]:
    if not summary:
        return ()
    text = summary if summary.endswith(".") else f"{summary}."
    return tuple(textwrap.wrap(text, width=64))


def _signature(method: Method) -> str:
    required = [f"{p.name}: {p.type}" for p in method.path_params]
    required += [
        f"{p.name}: {p.type}" for p in method.query_params if p.required
    ]
    if method.body:
        required.append(f"body: {method.body}")
    optional = [
        f"{p.name}: {p.type} | None = None"
        for p in method.query_params
        if not p.required
    ]
    parts = required + (["*", *optional] if optional else [])
    return "".join(f", {part}" for part in parts)


def _call(method: Method) -> str:
    parts = [method.name.upper()]
    if method.path_params:
        pairs = ", ".join(f'"{p.wire}": {p.name}' for p in method.path_params)
        parts.append(f"path={{{pairs}}}")
    if method.query_params:
        pairs = ", ".join(f'"{p.wire}": {p.name}' for p in method.query_params)
        parts.append(f"query={{{pairs}}}")
    if method.body:
        parts.append("body=body")
    return ", ".join(parts)


def _operation_class(method: Method) -> str:
    if method.kind == "no_content":
        return "NoContentOperation"
    if method.kind == "raw":
        return "RawOperation"
    return "Operation"


def _references(annotation: str) -> set[str]:
    return set(IDENTIFIER.findall(annotation))


def _field_line(field: Field) -> str:
    """field() нужен только ради repr=False, дефолт ставится напрямую."""
    value = _DEFAULTS.get(field.default or "", field.default)
    if not field.secret:
        default = f" = {value}" if value else ""
        return f"{field.name}: {field.type}{default}"

    options = ["repr=False"]
    if value is not None:
        options.append(f"default={value}")
    return f"{field.name}: {field.type} = field({', '.join(options)})"


def _sorted_fields(model: Model) -> Model:
    without = [f for f in model.fields if f.default is None]
    with_default = [f for f in model.fields if f.default is not None]
    fields = tuple(without + with_default)
    return Model(name=model.name, fields=fields, doc=model.doc)


def _ordered(models: tuple[Model, ...]) -> list[Model]:
    """Топологический порядок: иначе класс сослался бы на ещё не созданный."""
    by_name = {m.name: m for m in models}
    ordered: list[Model] = []
    done: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        if name in done or name not in by_name or name in active:
            return
        active.add(name)
        for field in by_name[name].fields:
            for reference in _references(field.type):
                visit(reference)
        active.discard(name)
        done.add(name)
        ordered.append(by_name[name])

    for model in models:
        visit(model.name)
    return ordered


def polish(root: Path) -> None:
    """Форматируем и подчищаем импорты тем же ruff, что и остальной код."""
    for args in (
        ["format", str(root)],
        ["check", "--fix", "--unsafe-fixes", "--quiet", str(root)],
    ):
        subprocess.run(["ruff", *args], check=False, capture_output=True)  # noqa: S603, S607
