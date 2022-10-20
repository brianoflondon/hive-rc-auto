import asyncio

import pytest
from hive_rc_auto.helpers.rc_delegation import (
    get_rc_of_accounts,
    get_rc_of_one_account,
    list_rc_direct_delegations,
    mill,
)


def test_mill():
    number = 33_000_000
    assert mill(number) == 33


@pytest.mark.asyncio
@pytest.mark.slow
async def test_find_rc_accounts():
    test_accounts = ["podping", "brianoflondon", "v4vapp"]
    all_rcs = await get_rc_of_accounts(check_accounts=test_accounts)
    assert len(all_rcs) == 3
    await asyncio.sleep(10)
    new_rcs = await get_rc_of_accounts(
        check_accounts=test_accounts, old_all_rcs=all_rcs
    )
    for old_rc, new_rc in zip(new_rcs, all_rcs):
        await new_rc.fill_delegations()
        assert old_rc.account == new_rc.account


@pytest.mark.asyncio
async def test_list_rc_direct_delegations():
    deleg_list = await list_rc_direct_delegations("podping")
    deleg_list2 = await list_rc_direct_delegations("podping", deleg_list[1].acc_to, 1)
    assert deleg_list[1] == deleg_list2[0]


@pytest.mark.asyncio
async def test_get_rc_of_one_account():
    podping_rc = await get_rc_of_one_account(check_account="podping")
    podping_rc = await get_rc_of_one_account(check_account="podping", old_rc=podping_rc)
    assert podping_rc.account == "podping"
