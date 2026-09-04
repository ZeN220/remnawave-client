"""Приём вебхуков панели.

Панель шлёт события на WEBHOOK_URL и подписывает тело ключом
WEBHOOK_SECRET_HEADER. Сервер здесь на стандартной библиотеке, чтобы
пример не тянул фреймворк: в своём приложении берите тело запроса как
есть и передавайте в receive().

    export WEBHOOK_SECRET=<значение WEBHOOK_SECRET_HEADER из .env панели>
    python examples/05_webhooks.py
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from remnawave.exceptions import RemnawaveError
from remnawave.webhooks import SIGNATURE_HEADER, WebhookReceiver

hooks = WebhookReceiver(os.environ["WEBHOOK_SECRET"])


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        # Именно сырые байты: подпись считается по ним, и повторная
        # сериализация разобранного JSON её ломает.
        body = self.rfile.read(length)
        signature = self.headers.get(SIGNATURE_HEADER, "")

        try:
            event = hooks.receive(body, signature)
        except RemnawaveError as error:
            print(f"отклонено: {error}")
            self.send_response(400)
            self.end_headers()
            return

        print(f"{event.scope:18} {event.event}")
        if event.scope == "user":
            print(f"   {event.data.username} -> {event.data.status}")

        self.send_response(200)
        self.end_headers()


HTTPServer(("", 8080), Handler).serve_forever()
