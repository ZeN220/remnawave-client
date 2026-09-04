from .auth import Auth


class BearerAuth(Auth):
    def __init__(self, token: str) -> None:
        if not token:
            message = "token must not be empty"
            raise ValueError(message)
        self._token = token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(token='***')"
