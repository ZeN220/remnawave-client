import os
from datetime import UTC, datetime, timedelta

from remnawave import Remnawave
from remnawave.exceptions import NotFoundError
from remnawave.types import CreateUserBody, UpdateUserBody, UserStatus

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    user = rw.users.create_user(
        CreateUserBody(
            username="example_user",
            expire_at=datetime.now(UTC) + timedelta(days=30),
            traffic_limit_bytes=50 * 1024**3,
            telegram_id=123456789,
        ),
    )
    print(f"создан id={user.id} short_uuid={user.short_uuid}")

    updated = rw.users.update_user(
        UpdateUserBody(id=user.id, description="из примера"),
    )
    print(f"описание: {updated.description!r}")
    print(f"telegram_id цел: {updated.telegram_id}")

    cleared = rw.users.update_user(UpdateUserBody(id=user.id, tag=None))
    print(f"tag: {cleared.tag!r}")

    disabled = rw.users.disable_user(user.id)
    is_disabled = disabled.status is UserStatus.DISABLED
    print(f"статус: {disabled.status} (DISABLED: {is_disabled})")

    rw.users.delete_user(user.id)
    print("удалён")

    try:
        rw.users.get_user_by_id(user.id)
    except NotFoundError as error:
        print(f"как и ожидалось: {error}")
        print(f"код ошибки: {error.error_code}")
