import logging
from hive_rc_auto.helpers.config import Config
import pytest
from hive_rc_auto.helpers.hive_calls import (
    get_client,
    get_delegated_posting_auth_accounts,
)
from lighthive.node_picker import compare_nodes


@pytest.mark.asyncio
async def test_get_client():
    client = get_client()
    new_list = await compare_nodes(nodes=client.node_list, logger=logging)
    client = get_client(nodes=new_list)
    try:
        first_node = client.current_node
        client.next_node()
        while not client.current_node == first_node:
            props = client.get_dynamic_global_properties()
            client.next_node()
    except Exception as ex:
        assert False

    assert True


@pytest.mark.asyncio
async def test_get_delegated_posting_auth_accounts():
    delegating_accounts = await get_delegated_posting_auth_accounts()
    assert delegating_accounts[0] == Config.PRIMARY_ACCOUNT
    delegating_accounts = await get_delegated_posting_auth_accounts("brianoflondon")
    assert delegating_accounts


@pytest.mark.asyncio
async def test_RCAllData_fill_data():
    pass
