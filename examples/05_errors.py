"""Error handling.

Everything the library raises inherits from RemnawaveError, so a single
except is enough to catch anything coming from it. Below that root the
hierarchy splits by what actually went wrong, which is what you usually
want to branch on.
"""

import os
from datetime import UTC, datetime

from remnawave import Remnawave
from remnawave.exceptions import (
    ApiError,
    ForbiddenError,
    NotFoundError,
    RemnawaveError,
    SerializationError,
    TooManyRequestsError,
    TransportError,
    UnauthorizedError,
)
from remnawave.types import CreateUserBody

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    try:
        rw.users.get_user_by_id(999_999)
    except NotFoundError as error:
        print(f"no such user: {error}")
        print(f"   status={error.status} code={error.error_code!r}")

    try:
        rw.users.get_user_by_username("definitely-not-here")
    except ApiError as error:
        if error.error_code == "A025":
            print("user not found by username")
        else:
            print(f"unexpected API error: {error}")

    try:
        rw.api_tokens.get_api_tokens()
    except UnauthorizedError:
        print("token is missing, expired or revoked")
    except ForbiddenError as error:
        print(f"token lacks access: {error.message}")

    try:
        rw.users.create_user(
            CreateUserBody(username="", expire_at=datetime.now(UTC)),
        )
    except ApiError as error:
        print(f"panel rejected the body: {error}")

    try:
        rw.system.get_stats()
    except TransportError as error:
        print(f"could not reach the panel: {type(error).__name__}: {error}")

    try:
        rw.nodes.get_nodes()
    except SerializationError as error:
        print(f"unexpected payload shape: {error}")

    # Rate limiting, if a proxy in front of the panel applies it.
    try:
        rw.users.get_users(size=1)
    except TooManyRequestsError:
        print("slow down")

    # One catch for everything the library can raise.
    try:
        rw.users.get_users()
    except RemnawaveError as error:
        print(f"{type(error).__name__}: {error}")
