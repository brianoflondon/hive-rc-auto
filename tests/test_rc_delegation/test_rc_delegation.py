import asyncio

import pytest
from hive_rc_auto.helpers.rc_delegation import (
    RCAllData,
    RCListOfAccounts,
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

@pytest.mark.slow
def test_get_rc_list_of_accounts():
    all_accounts = RCListOfAccounts()
    assert len(all_accounts.accounts) > 2


@pytest.mark.asyncio
async def test_RCAllData_fill_data():
    all_accounts = RCListOfAccounts(
        accounts=[
            "podping",
            "brianoflondon",
            "v4vapp.dhf",
            "adam.podping",
            "alecksgates",
            "andih",
            "benjaminbellamy",
            "blocktvnews",
            "dudesanddads",
            "hive-hydra",
            "hivehydra",
            "learn-to-code",
            "phoneboy",
            "podnews",
            "podping-git",
            "podping.aaa",
            "podping.adam",
            "podping.bbb",
            "podping.blubrry",
            "podping.bol",
            "podping.ccc",
            "podping.curio",
            "podping.ddd",
            "podping.eee",
            "podping.gittest",
            "podping.live",
            "podping.podverse",
            "podping.spk",
            "podping.test",
            "podping.win",
        ]
    )
    all_data = RCAllData(accounts=all_accounts.accounts)
    await all_data.fill_data()
    await asyncio.sleep(5)
    await all_data.fill_data(old_all_rcs=all_data.rcs)
    assert all_data
