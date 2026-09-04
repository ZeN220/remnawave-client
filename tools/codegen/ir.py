from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    type: str
    wire: str
    default: str | None = None
    secret: bool = False


@dataclass(frozen=True, slots=True)
class Model:
    name: str
    fields: tuple[Field, ...]
    doc: str | None = None


@dataclass(frozen=True, slots=True)
class Enum:
    name: str
    members: tuple[tuple[str, str], ...]
    doc: str | None = None


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    wire: str
    type: str
    required: bool


@dataclass(frozen=True, slots=True)
class Pagination:
    items_field: str
    item_type: str
    max_page_size: int


@dataclass(frozen=True, slots=True)
class Method:
    name: str
    http: str
    path: str
    kind: str
    returns: str | None = None
    body: str | None = None
    doc: str | None = None
    path_params: tuple[Param, ...] = ()
    query_params: tuple[Param, ...] = ()
    pagination: Pagination | None = None


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    class_name: str
    doc: str | None = None
    methods: tuple[Method, ...] = ()


@dataclass(frozen=True, slots=True)
class Webhook:
    scope: str
    type_name: str


@dataclass(frozen=True, slots=True)
class Api:
    version: str
    enums: tuple[Enum, ...] = ()
    models: tuple[Model, ...] = ()
    groups: tuple[Group, ...] = ()
    webhooks: tuple[Webhook, ...] = ()
    renames: dict[str, dict[str, str]] = field(default_factory=dict)
