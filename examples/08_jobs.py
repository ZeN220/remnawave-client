import os

from remnawave import Remnawave
from remnawave.exceptions import JobFailedError, JobTimeoutError
from remnawave.types import GeocheckByNodeBody

URL = os.environ["REMNAWAVE_URL"]
TOKEN = os.environ["REMNAWAVE_TOKEN"]

with Remnawave(URL, TOKEN) as rw:
    user = rw.users.get_users(start=0, size=1).users[0]
    node = rw.nodes.get_nodes()[0]

    connections = rw.connections.wait_connections_by_user(user.id)
    for seen in connections.nodes:
        ips = ", ".join(ip.ip for ip in seen.ips) or "none"
        print(f"{user.username} on {seen.node_name}: {ips}")

    try:
        report = rw.connections.wait_geocheck_by_node(
            node.uuid,
            GeocheckByNodeBody(ip="1.1.1.1"),
            interval=0.5,
            timeout=30,
        )
    except JobFailedError as error:
        print(f"the panel failed job {error.job_id}")
    except JobTimeoutError as error:
        print(f"job {error.job_id} did not finish in 30 s")
    else:
        print(f"geocheck of {node.name}: {report.message or 'done'}")
