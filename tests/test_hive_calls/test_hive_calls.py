import logging
import os
import subprocess
from timeit import default_timer as timer

import pytest
from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import (
    get_client,
    get_delegated_posting_auth_accounts,
    get_tracking_accounts,
    make_lighthive_call,
    publish_feed,
)
# from hived_rpc_scanner.runner import runner
from lighthive.node_picker import compare_nodes


@pytest.mark.asyncio
async def test_get_client():
    client = get_client()
    new_list = await compare_nodes(nodes=client.node_list, logger=logging)
    client = get_client(nodes=new_list)
    try:
        first_node = client.current_node
        while True:
            props = make_lighthive_call(
                client=client, call_to_make=client.get_dynamic_global_properties
            )
            logging.info(f"{client.current_node} - {props.get('head_block_number')}")
            client.next_node()
            if client.current_node == first_node:
                break
    except Exception as ex:
        assert False

    assert True


def test_get_tracking_accounts():
    ans = get_tracking_accounts()
    assert ans


@pytest.mark.asyncio
async def test_get_delegated_posting_auth_accounts():
    delegating_accounts = get_delegated_posting_auth_accounts()
    assert delegating_accounts[0] == Config.PRIMARY_ACCOUNT
    delegating_accounts = get_delegated_posting_auth_accounts("brianoflondon")
    assert delegating_accounts


@pytest.mark.asyncio
async def test_check_all_rpc_nodes():
    client = get_client()
    start_time = timer()
    nodes = [n for n in client.node_list]
    logging.info(f"hived_rpc_scanner --nodes {' '.join(nodes)}")
    nodes = "https://rpc.ecency.com"

@pytest.mark.asyncio
async def test_publish_feed():
    assert await publish_feed()