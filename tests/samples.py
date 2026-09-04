from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Nested:
    used_bytes: int
    online_at: datetime | None


@dataclass
class Sample:
    id: int
    short_uuid: str
    created_at: datetime
    nested: Nested


@dataclass
class Box(Generic[T]):
    response: T


@dataclass
class SamplePage:
    total: int
    users: list[Sample]
