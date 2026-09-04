from typing import Protocol, TypeVar

T = TypeVar("T")


class Serializer(Protocol):
    def load(self, raw: bytes, tp: type[T]) -> T: ...
    def dump(self, obj: T, tp: type[T] | None = None) -> bytes: ...
