import logging
import os
from typing import Any, Callable, List, Optional, Union

import backoff
import pymssql
from hive_rc_auto.helpers.config import Config
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException
from lighthive.helpers.account import VOTING_MANA_REGENERATION_IN_SECONDS
from lighthive.node_picker import compare_nodes

Config.VOTING_MANA_REGENERATION_IN_SECONDS = VOTING_MANA_REGENERATION_IN_SECONDS


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
        if os.getenv("PODPING_TESTNET", "False").lower() in (
            "true",
            "1",
            "t",
        ):
            nodes = [os.getenv("PODPING_TESTNET_NODE")]
            chain = {"chain_id": os.getenv("PODPING_TESTNET_CHAINID")}
        # else:
        #     nodes = [
        #         "https://api.hive.blog",
        #         "https://api.deathwing.me",
        #         "https://hive-api.arcange.eu",
        #         "https://api.openhive.network",
        #         "https://api.hive.blue",
        #     ]
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

    hive_acc = client.account(primary_account)
    return make_lighthive_call(client=client,call_to_make=hive_acc.following)



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
            logging.error(
                f"{client.current_node} {client.api_type} not returning useful results"
            )
            client.next_node()
            logging.warning(
                f"{client.current_node} trying"
            )
            counter -= 1
    raise Exception("Everything failed")
