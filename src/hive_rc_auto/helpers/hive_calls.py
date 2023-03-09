import json
import logging
import os
import re
from datetime import datetime, timedelta
from random import shuffle
from typing import Any, Callable, List, Optional, Union

import backoff
import httpx
import pymssql
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException
from lighthive.helpers.account import VOTING_MANA_REGENERATION_IN_SECONDS
from pydantic import BaseModel, Field

from hive_rc_auto.helpers.config import Config

Config.VOTING_MANA_REGENERATION_IN_SECONDS = VOTING_MANA_REGENERATION_IN_SECONDS


class HiveTrx(BaseModel):
    trx_id: str = Field(alias="id")
    block_num: int
    trx_num: int
    expired: bool


def get_client(
    posting_keys: Optional[List[str]] = None,
    nodes=None,
    connect_timeout=3,
    read_timeout=30,
    loglevel=logging.ERROR,
    chain=None,
    automatic_node_selection=False,
    api_type="condenser_api",
) -> Client:
    try:
        if os.getenv("TESTNET", "False").lower() in (
            "true",
            "1",
            "t",
        ):
            nodes = [os.getenv("TESTNET_NODE")]
            chain = {"chain_id": os.getenv("TESTNET_CHAINID")}
        else:
            nodes = [
                "https://rpc.podping.org",
                "https://hived.emre.sh",
                "https://api.hive.blog",
                "https://api.deathwing.me",
                # "https://hive-api.arcange.eu",
                # "https://api.openhive.network",
                "https://rpc.ausbit.dev",
            ]
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=automatic_node_selection,
            backoff_mode=backoff.fibo,
            backoff_max_tries=3,
            load_balance_nodes=True,
            circuit_breaker=True,
        )
        return client(api_type)
    except Exception as ex:
        logging.error("Error getting Hive Client")
        logging.exception(ex)
        raise ex


def get_delegated_posting_auth_accounts(
    primary_account=Config.PRIMARY_ACCOUNT,
) -> List[str]:
    """
    Return a list of all accounts which have delegated posting authority
    to the primary account. These accounts can be used to draw RC's from
    if the primary account is running low.

    The primary account is added to the start of the list
    """
    try:
        SQLCommand = (
            f"SELECT name FROM Accounts WHERE posting LIKE "
            f"'%\"{primary_account}\"%'"
        )
        result = hive_sql(SQLCommand, 100)

    except pymssql.OperationalError as e:
        logging.error("Unable to connect to HiveSQL")
        logging.error(e)
        # If there is a problem with HiveSQL falls back to hard coded list
        # found in the .env
        return [primary_account] + Config.DELEGATING_ACCOUNTS
    except Exception as e:
        logging.error(e)
        raise e
    ans = [primary_account] + [a[0] for a in result]
    return ans


def hive_sql(SQLCommand, limit):
    db = os.environ["HIVESQL"].split()
    conn = pymssql.connect(
        server=db[0],
        user=db[1],
        password=db[2],
        database=db[3],
        timeout=0,
        login_timeout=10,
    )
    cursor = conn.cursor()
    cursor.execute(SQLCommand)
    result = cursor.fetchmany(limit)
    conn.close()
    return result


def get_tracking_accounts(
    primary_account: str = Config.PRIMARY_ACCOUNT, client: Client = None
) -> List[str]:
    """
    Get a list of all accounts allowed to post by the primary account
    and only react to these accounts. Always returns the primary account
    as the first item in the list.

    This function must return a list of Strings but that can be generated
    any way you like.
    """
    if not client:
        client = get_client()

    hive_acc = make_lighthive_call(
        client=client, call_to_make=client.account, params=primary_account
    )
    # try:
    #     hive_acc = client.account(primary_account)
    # except Exception as e:
    #     logging.error(e)
    return make_lighthive_call(client=client, call_to_make=hive_acc.following)


def get_rcs(check_accounts: List[str]) -> dict:
    """ "
    Calls hive with the `find_rc_accounts` method
    """
    client_rc = get_client(api_type="rc_api")
    return make_lighthive_call(
        client=client_rc,
        call_to_make=client_rc.find_rc_accounts,
        params=({"accounts": check_accounts}),
    )


def price_feed_update_needed(base: float) -> bool:
    """
    Check if previous run of price feed has put an output file down and the
    age of the feed is less than 12 hours.
    Returns false if there is no need to update the feed.
    """
    try:
        if os.path.isfile("price_feed.json"):
            with open("price_feed.json", "r") as f:
                prev_ans = json.load(f)
                prev_base = prev_ans.get("base")
                prev_timestamp = prev_ans.get("timestamp")
            if prev_base and prev_timestamp:
                per_diff = abs(base - prev_base) / ((base + prev_base) / 2)
                quote_timediff = timedelta(
                    seconds=int(datetime.utcnow().timestamp() - prev_timestamp)
                )
                if abs(per_diff) < 0.02 and quote_timediff.total_seconds() < (
                    12 * 3600
                ):
                    logging.info(
                        f"Price feed un-changed | Base: {base:.3f} | "
                        f"Change: {per_diff*100:.1f} % | "
                        f"Age: {quote_timediff}"
                    )
                    return False
    except Exception as ex:
        logging.error(f"Problem checking old feed price {ex}")
    return True


async def publish_feed(publisher: str = "brianoflondon") -> bool:
    """Publishes a price feed to Hive"""
    try:
        resp = httpx.get("https://api.v4v.app/v1/cryptoprices/?use_cache=true")
        if resp.status_code == 200:
            rjson = resp.json()
            base: float = rjson["v4vapp"]["Hive_HBD"]
            if price_feed_update_needed(base):
                client = get_client(posting_keys=[Config.WITNESS_ACTIVE_KEY])
                op = Operation(
                    "feed_publish",
                    {
                        "publisher": publisher,
                        "exchange_rate": {
                            "base": f"{base:.3f} HBD",
                            "quote": "1.000 HIVE",
                        },
                    },
                )
                trx = client.broadcast_sync(op=op, dry_run=False)
                logging.info(f"Price feed published: {trx}")
                with open("price_feed.json", "w") as f:
                    json.dump(
                        {"base": base, "timestamp": datetime.utcnow().timestamp()}, f
                    )
        return True

    except Exception as ex:
        logging.exception(ex)
        logging.error(f"Exception publishing price feed: {ex}")
        return False


def make_lighthive_call(client: Client, call_to_make: Callable, params: Any = None):
    counter = len(client.node_list)
    while counter > 0:
        try:
            if params:
                response = call_to_make(params)
            else:
                response = call_to_make()
            return response
        except Exception as ex:
            logging.error(f"{client.current_node} {client.api_type} Failing: {ex}")
            client.next_node()
            logging.warning(f"Trying new node: {client.current_node}")
            counter -= 1
    raise Exception("Everything failed")


async def construct_operation(
    payload: dict,
    hive_operation_id: str,
    required_auth: str = None,
    required_posting_auth: str = None,
) -> Operation:
    """Build the operation for the blockchain"""
    payload_json = json.dumps(payload, separators=(",", ":"), default=str)
    if required_auth == None:
        required_auths = []
    else:
        required_auths = [required_auth]
    if required_posting_auth == None:
        required_posting_auths = []
    else:
        required_posting_auths = [required_posting_auth]

    op = Operation(
        "custom_json",
        {
            "required_auths": required_auths,
            "required_posting_auths": required_posting_auths,
            "id": str(hive_operation_id),
            "json": payload_json,
        },
    )
    logging.info(op.op_value)
    return op


async def send_custom_json(
    client: Client,
    payload: dict,
    hive_operation_id: str,
    required_auth: str = None,
    required_posting_auth: str = None,
) -> Union[None, HiveTrx]:
    """Build and send an operation to the blockchain"""
    try:
        trx = None
        op = await construct_operation(
            payload,
            hive_operation_id,
            required_auth=required_auth,
            required_posting_auth=required_posting_auth,
        )
        trx = client.broadcast_sync(op=op, dry_run=False)

        logging.info(f"Json sent via Lighthive Node: {client.current_node}")
        logging.info(f"{trx}")
        logging.info(f"https://hive.ausbit.dev/tx/{trx.get('id')}")
        logging.info(f"https://hiveblocks.com/tx/{trx.get('id')}")
        logging.info(payload)
        if trx:
            return HiveTrx.parse_obj(trx)

    except RPCNodeException as ex:
        logging.error(f"send_custom_json error: {ex}")
        try:
            if re.match(
                r".*same amount of RC already exist.*",
                ex.raw_body["error"]["message"],
            ):
                logging.info(ex.raw_body["error"]["message"])
                logging.info("No changes to delegation")
            elif re.match(
                r"plugin exception.*custom json.*",
                ex.raw_body["error"]["message"],
            ):
                logging.info(ex.raw_body["error"]["message"])
                logging.info("Unhandled RPC error")
                client.next_node()
                raise ex
            else:
                raise ex
        except (KeyError, AttributeError):
            logging.error(f"{ex}")
            logging.info("Non standard error message from RPC Node")
            raise ex

    except Exception as ex:
        logging.error(f"{ex}")
        raise ex
