import asyncio
import logging

import pytest
from hive_rc_auto.helpers.rc_delegation import (
    RCAllData,
    RCListOfAccounts,
    get_rc_of_accounts,
    list_rc_direct_delegations,
    mill,
    mill_s,
)


def test_mill():
    number = 33_000_000
    assert mill(number) == 33


@pytest.mark.asyncio
async def test_list_rc_direct_delegations():
    deleg_list = await list_rc_direct_delegations("podping")
    if deleg_list:
        deleg_list2 = await list_rc_direct_delegations(
            "podping", deleg_list[0].acc_to, 1
        )
        assert deleg_list[0] == deleg_list2[0]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_get_rc_list_of_accounts_and_fill_data():
    # Find all the accounts
    all_accounts = RCListOfAccounts()
    assert len(all_accounts.all) > 0
    assert len(all_accounts.delegating) + len(all_accounts.receiving) > 0
    # Fill all the data
    all_data = RCAllData(accounts=all_accounts)
    await all_data.fill_data()
    await asyncio.sleep(0.5)
    # Fill update the data
    await all_data.fill_data(old_all_rcs=all_data.rcs)
    assert all_data

    # await all_data.store_all_data()

    # Check for which account should delegate.
    amount_range = [1e9, 1e10, 1e11, 1.5e12, 3e12, 4e12, 5e12, 7e12, 1e13, 1e14, 1e15]
    for acc in all_accounts.receiving:
        for amount in amount_range:
            answer = await all_data.which_account_to_delegate_from(
                target=acc, amount=amount
            )
            logging.info(f"{answer:>16} -> {acc:>16} | {mill_s(amount)}")
            pass
