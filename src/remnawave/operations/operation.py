from dataclasses import dataclass
from typing import Any, Generic, TypeAlias, TypeVar

from .pagination import Pagination

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True, slots=True)
class Operation(Generic[T_co]):
    method: str
    path: str
    returns: type[T_co]
    pagination: Pagination | None = None


@dataclass(frozen=True, slots=True)
class NoContentOperation:
    method: str
    path: str


@dataclass(frozen=True, slots=True)
class RawOperation:
    """
    For subscription-raw endpoints
    """

    method: str
    path: str


AnyOperation: TypeAlias = "Operation[Any] | NoContentOperation | RawOperation"
