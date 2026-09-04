# Examples

```bash
export REMNAWAVE_URL=https://panel.example.com
export REMNAWAVE_TOKEN=<API token>

python examples/01_quickstart.py
```

Get the token from the admin dashboard, **API keys** tab. The JWT returned by
`POST /api/auth/login` will not work: it is a dashboard session with the
`ADMIN` role, and the panel refuses it for API requests. Only `API` tokens are
accepted.

| file | what it shows |
|---|---|
| `01_quickstart.py` | first request: system stats and a page of users |
| `02_async.py` | async client, concurrent calls, `async for` |
| `03_users_crud.py` | create, partial update, delete |
| `04_pagination.py` | walking listings with `iter_*` |
| `05_errors.py` | the exception hierarchy and what to branch on |
| `06_customization.py` | custom auth, transport and retry policy |
| `07_webhooks.py` | receiving webhooks and verifying the signature |

`07_webhooks.py` takes a different variable — the value of
`WEBHOOK_SECRET_HEADER` from the panel's `.env`:

```bash
export WEBHOOK_SECRET=<secret>
python examples/07_webhooks.py
```

It listens on port 8080 through `http.server` so the example does not pull in
a web framework. In your own application pass the **raw request body** to
`receive()` unchanged: the signature is computed over those exact bytes, and
re-serialising parsed JSON breaks the comparison.

## Notes

**Pagination.** `iter_*` fetches the next page only when the previous one runs
out, and clamps the page size to the maximum the endpoint declares.

**Retries.** `GET`, `HEAD`, `PUT` and `DELETE` are retried on transport
failures and on 429/5xx. `POST` and `PATCH` are not: a repeated
`POST /api/users/bulk/extend-expiration-date` would extend subscriptions
twice.
