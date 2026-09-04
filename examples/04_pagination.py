import os

from remnawave import Remnawave

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    page = rw.users.get_users(start=0, size=25)
    print(f"страница: {len(page.users)} из {page.total}")

    active = 0
    for user in rw.users.iter_users(page_size=500):
        active += user.status == "ACTIVE"
    print(f"активных: {active}")

    for record in rw.infra_billing.iter_infra_billing_records():
        print(f"  счёт {record.amount} от {record.billed_at:%Y-%m-%d}")
