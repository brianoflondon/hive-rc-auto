import asyncio
import logging

import pytest
from hive_rc_auto.helpers.rc_delegation import RCAllData, RCListOfAccounts


@pytest.mark.asyncio
async def test_update_delegations():
    all_accounts = RCListOfAccounts()
    all_data = RCAllData(accounts=all_accounts)
    await all_data.fill_data()
    all_data.log_output(logging.info)
    await all_data.update_delegations()
    all_data.log_output(logging.info)
    assert True