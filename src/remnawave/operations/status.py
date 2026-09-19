from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class JobStatus(Protocol[T_co]):
    @property
    def is_completed(self) -> bool: ...

    @property
    def is_failed(self) -> bool: ...

    @property
    def result(self) -> T_co | None: ...
