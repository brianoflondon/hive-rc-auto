import logging
import os
import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

# Mongo moved onto the replica set named in this project's .env.
# These keys are reapplied after load so a stale process value cannot
# keep the app on a retired host. When the image has no .env, Compose's
# environment is left as-is.
_MONGO_ENV_KEYS = (
    "DB_CONNECTION",
    "PINGSLURP_DB_CONNECTION",
    "DB_NAME",
    "ROOT_DB_NAME",
)


def _project_env_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_project_env() -> None:
    env_path = _project_env_path()
    if env_path is None:
        load_dotenv()
        return
    load_dotenv(env_path)
    for key, value in dotenv_values(env_path).items():
        if key in _MONGO_ENV_KEYS and value:
            os.environ[key] = value


load_project_env()


debug = False
logging.basicConfig(
    level=logging.INFO if not debug else logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(module)-14s %(lineno) 5d : %(message)s",
    datefmt="%m-%dT%H:%M:%S",
)


class Config:
    try:
        PRIMARY_ACCOUNT: str = os.getenv("PRIMARY_ACCOUNT")
        DELEGATING_ACCOUNTS: list[str] = os.getenv("DELEGATING_ACCOUNTS").split(",")

        POSTING_KEY: str = os.getenv("HIVE_POSTING_KEY")
        WITNESS_ACTIVE_KEY: str = os.getenv("WITNESS_ACTIVE_KEY")
        UPDATE_FREQUENCY_SECS: int = int(os.getenv("UPDATE_FREQUENCY_SECS"))  # in Minutes

        RC_BASE_LEVEL: int = int(os.getenv("RC_BASE_LEVEL"))
        RC_PCT_LOWER_TARGET: float = float(os.getenv("RC_PCT_LOWER_TARGET"))
        RC_PCT_UPPER_TARGET: float = float(os.getenv("RC_PCT_UPPER_TARGET"))
        RC_PCT_ALARM_LEVEL: float = float(os.getenv("RC_PCT_ALARM_LEVEL"))

        TESTNET: bool = os.getenv("TESTNET", "False").lower() in (
            "true",
            "1",
            "t",
        )
        TESTNET_NODE: list[str] = [os.getenv("TESTNET_NODE")]
        TESTNET_CHAINID: str = {"chain_id": os.getenv("TESTNET_CHAINID")}

        DB_CONNECTION = os.getenv("DB_CONNECTION")
        DB_NAME = os.getenv("DB_NAME")
        if TESTNET:
            DB_NAME = "testnet_" + DB_NAME

        DB_NAME_DELEG = DB_NAME + "_deleg"

        if not DB_CONNECTION:
            DB_CONNECTION = "mongodb://127.0.0.1:27017"
        # Same replica set as DB_CONNECTION. authSource stays pingslurp.
        PINGSLURP_DB_CONNECTION = os.getenv("PINGSLURP_DB_CONNECTION") or DB_CONNECTION

        MINIMUM_DELEGATION = 10_000_000_000

    except AttributeError as ex:
        logging.exception(ex)
        logging.error("ENV File not found or not correct")
        sys.exit(10)
