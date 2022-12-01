import asyncio
import logging
import os
from datetime import datetime
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import publish_feed
from hive_rc_auto.helpers.rc_delegation import (
    RCAccount,
    RCAllData,
    RCListOfAccounts,
    setup_mongo_db,
)


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
        await all_data.get_payload_for_pending_delegations(send_json=True)
        asyncio.create_task(all_data.store_all_data())
        old_all_rcs = all_data.rcs
        await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)


async def keep_publishing_price_feed():
    """
    Publishes a price feed for my witness, this will move to its own project soon
    """
    while True:
        success = await publish_feed()
        if success:
            await asyncio.sleep(60*600)
        else:
            await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)

async def check_db():
    logging.info(Config.DB_CONNECTION)
    try:
        server_info = await AsyncIOMotorClient(
            Config.DB_CONNECTION, serverSelectionTimeoutMS=5000
        ).server_info()
    except ServerSelectionTimeoutError as ex:
        logging.error("Bad database connection: %s", Config.DB_CONNECTION)
        raise ex
    except Exception as ex:
        logging.exception(ex)


async def main_loop():
    # Setup the data
    await check_db()
    setup_mongo_db()
    tasks = [update_rc_accounts(), keep_publishing_price_feed()]
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

    # asyncio.run(main_loop())

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Terminated with Ctrl-C")
    except asyncio.CancelledError:
        logging.info("Asyncio cancelled")

    except Exception as ex:
        logging.exception(ex)
        logging.error(ex)
