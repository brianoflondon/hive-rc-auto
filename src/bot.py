import asyncio
import logging
import os
from datetime import datetime

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.rc_delegation import RCAllData, RCListOfAccounts


async def main_loop():
    # Setup the data
    all_accounts = RCListOfAccounts()
    old_all_rcs = None
    while True:
        all_data = RCAllData(accounts = all_accounts)
        await all_data.fill_data(old_all_rcs=old_all_rcs)
        old_all_rcs = all_data.rcs
        await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)


if __name__ == "__main__":
    debug = False
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(module)-14s %(lineno) 5d : %(message)s",
        datefmt="%m-%dT%H:%M:%S",
    )
    logging.info("----------------------------------------")
    logging.info(f"Running at {datetime.now()}")
    logging.info(f"Testnet: {os.getenv('TESTNET')}")
    logging.info("----------------------------------------")
    # asyncio.run(main_loop())

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Terminated with Ctrl-C")
    except asyncio.CancelledError:
        logging.info("Asyncio cancelled")

    except Exception as ex:
        logging.error(ex.__class__)
