"""Первый запрос.

    export REMNAWAVE_URL=https://panel.example.com
    export REMNAWAVE_TOKEN=<API-токен из админки>
    python examples/01_quickstart.py

Токен нужен именно API-токен (вкладка API-keys в админке). JWT, который
выдаёт вход по паролю, панель для API-запросов не принимает.
"""

import os

from remnawave import Remnawave

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    stats = rw.system.get_stats()
    print(f"пользователей: {stats.users.total_users}")
    print(f"аптайм: {stats.uptime:.0f} c")
    print(f"нод онлайн: {stats.nodes.total_online}")

    page = rw.users.get_users(size=5)
    print(f"\nвсего {page.total}, первые {len(page.users)}:")
    for user in page.users:
        until = f"{user.expire_at:%Y-%m-%d}"
        print(f"  {user.username:24} {user.status:8} до {until}")
