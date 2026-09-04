# remnawave-client

Sync and async client for the [Remnawave](https://docs.rw) API, generated from
the panel's OpenAPI specification.


```bash
pip install remnawave-client
```

Requires Python 3.11 or newer.

## Versions

The library version equals the API version it was generated from. A tag exists
for every minor release of the panel from 2.0 onwards, so pin the one matching
your deployment:

```bash
pip install remnawave-client==3.0.0
```

## Quick start

```python
from remnawave import Remnawave

with Remnawave("https://panel.example.com", token) as rw:
    user = rw.users.get_user_by_username("zen")
    print(user.username, user.status, user.expire_at)

    for u in rw.users.iter_users():
        print(u.username)
```

The async client mirrors it:

```python
import asyncio

from remnawave import AsyncRemnawave

async def main() -> None:
    async with AsyncRemnawave("https://panel.example.com", token) as rw:
        stats = await rw.system.get_stats()
        nodes = await rw.nodes.get_nodes()
        async for user in rw.users.iter_users():
            print(user.username)

asyncio.run(main())
```

More in [`examples/`](examples/): pagination, partial updates, error handling,
webhooks and swapping out the client's parts.

## Errors

Everything the library raises inherits from `RemnawaveError`. Below it the
hierarchy splits by cause: `ApiError` for anything the panel answered with,
`TransportError` when the request never got a reply, `SerializationError` when
the payload did not match the schema.

```python
from remnawave.exceptions import NotFoundError

try:
    rw.users.get_user_by_id(42)
except NotFoundError as error:
    print(error.status, error.error_code)  # 404 'A025'
```

`error_code` is the panel's own code and is more specific than the HTTP
status — branch on it when you need to tell cases apart.

## Webhooks

```python
from remnawave.webhooks import SIGNATURE_HEADER, WebhookReceiver

hooks = WebhookReceiver(secret=os.environ["WEBHOOK_SECRET_HEADER"])
event = hooks.receive(request.body, request.headers[SIGNATURE_HEADER])

if event.scope == "user":
    print(event.event, event.data.username)
```

Pass the raw request body: the signature covers those exact bytes, so
re-serialising parsed JSON breaks verification.

## Regenerating

`src/remnawave/_generated/` is machine-written and must not be edited by hand.
To target another panel version, drop its specification into `specs/` and run:

```bash
python -m tools.codegen 3.4.3
```

Where the specification is wrong or awkward, `overlay.yaml` patches it before
generation: type names, forced field types, fields kept out of `repr`. Editing
the generated code directly would be lost on the next run; editing the vendored
specification would be lost on the next update.
