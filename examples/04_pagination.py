"""Обход листингов.

Панель отдаёт списки страницами. Методы iter_* обходят их лениво:
следующая страница запрашивается, только когда закончилась предыдущая.
"""

import os

from remnawave import Remnawave

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    # Страница целиком, если нужен total или своё управление смещением.
    page = rw.users.get_users(start=0, size=25)
    print(f"страница: {len(page.users)} из {page.total}")

    # Все пользователи одним потоком. Размер страницы берётся максимальный
    # из спеки, но его можно задать; больше максимума не запросится.
    active = 0
    for user in rw.users.iter_users(page_size=500):
        active += user.status == "ACTIVE"
    print(f"активных: {active}")

    # Так же устроены остальные листинги.
    for record in rw.infra_billing.iter_infra_billing_records():
        print(f"  счёт {record.amount} от {record.billed_at:%Y-%m-%d}")
