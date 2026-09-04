from typing import Protocol


class Auth(Protocol):
    def headers(self) -> dict[str, str]: ...
