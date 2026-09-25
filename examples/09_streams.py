import asyncio
import os

from redis.asyncio import Redis

from remnawave.streams.redis import AsyncRedisStreams

redis = Redis.from_url(os.environ["REDIS_URL"])
streams = AsyncRedisStreams(redis, group="example")


async def watch_traffic() -> None:
    async for entry in streams.user_usage(auto_ack=True):
        for record in entry.message.records:
            print(f"user {record.user_id}: +{record.total_bytes} bytes")


async def watch_subscriptions() -> None:
    requests = streams.subscription_requests()
    async for entry in requests:
        request = entry.message
        print(
            f"user {request.user_id} fetched subscription: {request.user_agent}"
        )
        await requests.ack(entry)


async def watch_connections() -> None:
    nodes = streams.node_connections()
    while True:
        entries = await nodes.read()
        for entry in entries:
            online = len(entry.message.users)
            print(f"node {entry.message.node_id}: {online} online")
        await nodes.ack(*entries)


async def main() -> None:
    await asyncio.gather(
        watch_traffic(),
        watch_subscriptions(),
        watch_connections(),
    )


asyncio.run(main())
