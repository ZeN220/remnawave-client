import json
from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar

from adaptix import (
    NameStyle,
    Provider,
    ProviderNotFoundError,
    Retort,
    name_mapping,
)
from adaptix.load_error import LoadError

from remnawave.exceptions import SerializationError

from .serializer import Serializer

T = TypeVar("T")

JsonLoads: TypeAlias = Callable[[bytes], Any]
JsonDumps: TypeAlias = Callable[[object], bytes]


class AdaptixSerializer(Serializer):
    def __init__(
        self,
        retort: Retort | None = None,
        loads: JsonLoads | None = None,
        dumps: JsonDumps | None = None,
    ) -> None:
        self._retort = retort or build_default_retort()
        self._loads = loads or json.loads
        self._dumps = dumps or _dumps

    def load(self, raw: bytes, tp: type[T]) -> T:
        try:
            data = self._loads(raw)
            loaded: T = self._retort.load(data, tp)
        except (LoadError, ValueError) as exc:
            raise SerializationError(str(exc)) from exc

        return loaded

    def dump(self, obj: T, tp: type[T] | None = None) -> bytes:
        try:
            data = self._retort.dump(obj, tp)
            dumped = self._dumps(data)
        except (ProviderNotFoundError, TypeError, ValueError) as exc:
            raise SerializationError(str(exc)) from exc

        return dumped


def build_default_retort(*extra: Provider) -> Retort:
    # omit_default: поля тела запроса объявлены как Omittable с Omitted()
    # по умолчанию — без этого «не отправлено» ушло бы на сервер как null.
    return Retort(
        recipe=[
            *extra,
            name_mapping(name_style=NameStyle.CAMEL, omit_default=True),
        ],
    )


def _dumps(data: object) -> bytes:
    return json.dumps(data, separators=(",", ":")).encode()
