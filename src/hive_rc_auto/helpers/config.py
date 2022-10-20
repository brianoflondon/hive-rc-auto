import logging
import os
import sys
from typing import List

from dotenv import load_dotenv

load_dotenv()


debug = False
logging.basicConfig(
    level=logging.INFO if not debug else logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(module)-14s %(lineno) 5d : %(message)s",
    datefmt="%m-%dT%H:%M:%S",
)

class Config:
    try:
        PRIMARY_ACCOUNT: str = os.getenv('PRIMARY_ACCOUNT')
        DELEGATING_ACCOUNTS: List[str] = os.getenv("DELEGATING_ACCOUNTS").split(",")

        POSTING_KEY: str = os.getenv("HIVE_POSTING_KEY")
        UPDATE_FREQUENCY_SECS: int = int(
            os.getenv("UPDATE_FREQUENCY_SECS")
        )  # in Minutes

        RC_BASE_LEVEL: int = int(os.getenv("RC_BASE_LEVEL"))
        RC_PCT_LOWER_TARGET: float = float(os.getenv("RC_PCT_LOWER_TARGET"))
        RC_PCT_UPPER_TARGET: float = float(os.getenv("RC_PCT_UPPER_TARGET"))
        RC_PCT_ALARM_LEVEL: float = float(os.getenv("RC_PCT_ALARM_LEVEL"))

        TESTNET: bool = os.getenv("TESTNET", "False").lower() in (
            "true",
            "1",
            "t",
        )
        TESTNET_NODE: List[str] = [os.getenv("TESTNET_NODE")]
        TESTNET_CHAINID: str = {"chain_id": os.getenv("TESTNET_CHAINID")}
    except AttributeError as ex:
        logging.exception(ex)
        logging.error("ENV File not found or not correct")
        sys.exit(10)
