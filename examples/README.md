# Примеры

Всем, кроме вебхуков, нужны две переменные окружения:

```bash
export REMNAWAVE_URL=https://panel.example.com
export REMNAWAVE_TOKEN=<API-токен>
```

Токен берётся в админке на вкладке API-keys. JWT, который выдаёт вход по
паролю, панель для API-запросов **не принимает** — она отвечает
`403 For API requests you must create own API-token in the admin dashboard`.

| файл | о чём |
|---|---|
| `01_quickstart.py` | первый запрос: статистика и список пользователей |
| `02_async.py` | асинхронный клиент, параллельные запросы, `async for` |
| `03_users_crud.py` | создание, частичное изменение, удаление, ошибки |
| `04_pagination.py` | обход листингов через `iter_*` |
| `05_webhooks.py` | приём вебхуков со сверкой подписи |
| `06_customization.py` | своя авторизация, транспорт и политика повторов |

Для `05_webhooks.py` нужна другая переменная — значение
`WEBHOOK_SECRET_HEADER` из `.env` панели:

```bash
export WEBHOOK_SECRET=<секрет>
python examples/05_webhooks.py
```
