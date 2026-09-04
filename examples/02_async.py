import asyncio
import os

from remnawave import AsyncRemnawave


async def main() -> None:
    url, token = os.environ["REMNAWAVE_URL"], os.environ["REMNAWAVE_TOKEN"]

    async with AsyncRemnawave(url, token) as rw:
        stats, nodes, page = await asyncio.gather(
            rw.system.get_stats(),
            rw.nodes.get_nodes(),
            rw.users.get_users(size=3),
        )
        print(f"аптайм {stats.uptime:.0f} c")
        print(f"нод {len(nodes)}, юзеров {page.total}")

        async for user in rw.users.iter_users():
            print(" ", user.username)


asyncio.run(main())
