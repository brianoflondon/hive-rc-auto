import asyncio
import logging
import os
from datetime import datetime
from typing import List

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.rc_delegation import RCAccount, RCAllData, RCListOfAccounts


async def update_rc_accounts():
    """
    Update all the accounts in a loop
    """
    all_accounts = RCListOfAccounts()
    old_all_rcs = None
    while True:
        all_data = RCAllData(accounts=all_accounts)
        await all_data.fill_data(old_all_rcs=old_all_rcs)
        await all_data.update_delegations()
        all_data.log_output(logger=logging.info)
        old_all_rcs = all_data.rcs
        await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)


async def main_loop():
    # Setup the data
    tasks = [update_rc_accounts()]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    debug = False
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(module)-14s %(lineno) 5d : %(message)s",
        datefmt="%m-%dT%H:%M:%S",
    )
    logging.info(f"-------{__file__}----------------------")
    logging.info(f"Running at {datetime.now()}")
    logging.info(f"Testnet: {os.getenv('TESTNET')}")
    logging.info(f"-------{__file__}----------------------")

    asyncio.run(main_loop())

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Terminated with Ctrl-C")
    except asyncio.CancelledError:
        logging.info("Asyncio cancelled")

    except Exception as ex:
        logging.error(ex.__class__)
