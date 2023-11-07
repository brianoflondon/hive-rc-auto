import os
import uuid
from datetime import datetime

import pytest
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import construct_operation

os.environ["TESTNET"] = "false"
hive_operation_id = "bol_testing"


async def local_construct_operation(node: str):
    payload = {"node": node, "datetime": datetime.utcnow()}
    op = await construct_operation(
        hive_operation_id=hive_operation_id,
        payload=payload,
        required_posting_auth=Config.PRIMARY_ACCOUNT,
    )
    return op


@pytest.mark.asyncio
async def test_all_nodes_send_custom_json():
    nodes = [
        "https://rpc.podping.org",
        "https://hived.emre.sh",
        "https://api.hive.blog",
        "https://hive-api.arcange.eu",
        "https://api.openhive.network",
        "https://rpc.ausbit.dev",
    ]

    results = {}
    for node in nodes:
        op = await local_construct_operation(node=node)
        client = Client(nodes=[node], keys=[Config.POSTING_KEY])
        try:
            _ = client.broadcast_sync(op=op, dry_run=False)
            print(f"Pass: {node}")
            results[node] = True
        except RPCNodeException as e:
            print(f"Fail: {node} - {e}")
            results[node] = False

        except Exception as e:
            print(f"Fail: {node} - {e}")
            results[node] = False
    for node in results:
        print(f"Result: {node} - {results[node]}")
