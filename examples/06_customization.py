import os

import httpx

from remnawave import Remnawave
from remnawave.execution import Auth, ExponentialBackoff
from remnawave.http import HttpxSync

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]


class CaddyAuth(Auth):
    def __init__(self, token: str, api_key: str) -> None:
        self._token = token
        self._api_key = api_key

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Api-Key": self._api_key,
        }


client = Remnawave(
    URL,
    auth=CaddyAuth(TOKEN, os.environ.get("CADDY_API_KEY", "")),
    transport=HttpxSync(httpx.Client(proxy=os.environ.get("HTTPS_PROXY"))),
    retry=ExponentialBackoff(attempts=5, base=0.3, max_delay=10.0),
    timeout=15.0,
)

with client as rw:
    print(rw.system.get_stats().uptime)
