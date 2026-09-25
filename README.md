# remnawave-client

Sync and async client for the [Remnawave](https://docs.rw) API, generated from
the panel's OpenAPI specification.


```bash
pip install remnawave-client
```

Requires Python 3.11 or newer.

## Versions

The first three numbers of the library version are the panel version it was
generated from; a fourth one counts the library's own releases on top of it.
`1.2.3` is the first release for panel 1.2.3, `1.2.3.1` and `1.2.3.2` bring
fixes and features of the library itself while the API stays the same.

A release exists for every minor version of the panel from 2.0 onwards. Pin the
panel version you run and let the fourth number float, so library fixes still
arrive:

```bash
pip install "remnawave-client==1.2.3.*"
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

## Background jobs

Some checks run as panel jobs: one request starts the job and returns a
`jobId`, another polls its status. `wait_*` does both and returns the result:

```python
result = rw.connections.wait_connections_by_user(user_id, timeout=120)
for node in result.nodes:
    print(node.node_name, [ip.ip for ip in node.ips])
```

A job the panel reports as failed raises `JobFailedError`; one still running
after `timeout` seconds raises `JobTimeoutError`. The underlying start and
poll methods stay available.

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

## Redis streams

With `EXPORT_TO_STREAM_ENABLED=true` the panel exports per-user traffic,
subscription requests and node connections to Redis streams. Install the
`streams` extra and read them through a consumer group on the panel's Redis:

```bash
pip install "remnawave-client[streams]"
```

```python
from redis import Redis
from remnawave.streams.redis import RedisStreams

streams = RedisStreams(Redis(), group="billing")
usage = streams.user_usage()

for entry in usage:
    for record in entry.message.records:
        print(entry.message.node_id, record.user_id, record.total_bytes)
    usage.ack(entry)
```

`user_usage()`, `subscription_requests()` and `node_connections()` each return
a consumer of one stream; `AsyncRedisStreams` does the same over a
`redis.asyncio.Redis`. Every service needs a group of its own: consumers
sharing a group split the messages between them. Several workers of one service
share a group and pass distinct `name`s; a single worker can leave the default.
The group is created on the first read and starts at the end of the stream
(`start_id="0"` reads what the panel still keeps). Delivery is at-least-once:
an entry stays pending until acknowledged and is delivered again after a
restart. A message that does not parse raises `StreamMessageError`; acknowledge
its `entry_id` to skip it. With `auto_ack=True` a batch is acknowledged when
the next `read()` starts, so iterating acknowledges whatever the loop body got
through; the batch in hand when the process dies comes back after a restart.
The panel trims the streams (`EXPORT_TO_STREAM_MAXLEN`, one hour for node
connections), so a consumer that falls behind loses entries.

Without a consumer, `USER_USAGE.parse(fields)` from `remnawave.streams.stream`
turns the fields of one stream entry into a message.

## Regenerating

`src/remnawave/_generated/` is machine-written and must not be edited by hand.
Regenerating it against the version the package declares takes no arguments:

```bash
python -m tools.codegen
```

To move the project onto a newer panel release, drop its specification into
`specs/` and pass the version once:

```bash
python -m tools.codegen <version>
```

Where the specification is wrong or awkward, `overlay.yaml` patches it before
generation: type names, forced field types, fields kept out of `repr`. Editing
the generated code directly would be lost on the next run; editing the vendored
specification would be lost on the next update.
