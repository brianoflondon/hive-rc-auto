import logging

import pytest
from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import (
    get_client,
    get_delegated_posting_auth_accounts,
    make_lighthive_call,
)
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


@pytest.mark.asyncio
async def test_get_delegated_posting_auth_accounts():
    delegating_accounts = get_delegated_posting_auth_accounts()
    assert delegating_accounts[0] == Config.PRIMARY_ACCOUNT
    delegating_accounts = get_delegated_posting_auth_accounts("brianoflondon")
    assert delegating_accounts
