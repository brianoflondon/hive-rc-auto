import asyncio
import logging
from typing import List

import pytest
from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.rc_delegation import (
    RCAllData,
    RCDirectDelegation,
    RCListOfAccounts,
)


@pytest.mark.asyncio
async def test_update_delegations():
    all_accounts = RCListOfAccounts()
    all_data = RCAllData(accounts=all_accounts)
    await all_data.fill_data()
    all_data.log_output(logging.info)
    await all_data.update_delegations()
    all_data.log_output(logging.info)
    assert True


@pytest.mark.asyncio
async def test_send_delegations_custom_json():
    all_accounts = RCListOfAccounts()
    all_data = RCAllData(accounts=all_accounts)
    test_accounts = ["flyingboy", "surfingboy"]
    all_deleg: List[RCDirectDelegation] = []
    for acc in all_accounts.delegating:
        for test_acc in test_accounts:
            new_dd = RCDirectDelegation.parse_obj(
                {
                    "from": acc,
                    "to": test_acc,
                    "delegated_rc": Config.MINIMUM_DELEGATION,
                    "cut": False,
                }
            )
            all_deleg.append(new_dd)
    [dd.log_line_output(logging.info) for dd in all_deleg]
    all_data.pending_delegations = all_deleg
    payloads = await all_data.get_payload_for_pending_delegations()
    assert len(payloads) == len(all_accounts.delegating)
    payloads = await all_data.get_payload_for_pending_delegations(send_json=True)
    assert payloads