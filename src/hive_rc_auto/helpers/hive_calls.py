import logging
import os
from typing import List, Optional

from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException
from lighthive.helpers.account import VOTING_MANA_REGENERATION_IN_SECONDS
from lighthive.node_picker import compare_nodes

from hive_rc_auto.helpers.config import Config

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
        if Config.TESTNET:
            nodes = Config.TESTNET_NODE
            chain = Config.TESTNET_CHAIN
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=automatic_node_selection,
        )
        return client(api_type)
    except Exception as ex:
        raise ex


def tracking_accounts(
    primary_accounts: List[str] = None, client: Client = None
) -> List[str]:
    """
    Get a list of all accounts allowed to post by the primary account
    and only react to these accounts. Always returns the primary account
    as the first item in the list.

    This function must return a list of Strings but that can be generated
    any way you like.
    """
    if not primary_accounts:
        primary_accounts = Config.DELEGATING_ACCOUNTS.copy()

    if not client:
        client = get_client()
    try:
        primary_account = client.account(primary_accounts[0])
        following = sorted(primary_account.following())
        return following
    except RPCNodeException as ex:
        logging.error("Failure to find following accounts, trying normal APIs")
        logging.error(ex)
        client = Client()
        primary_account = client.account(primary_accounts[0])
        following = sorted(primary_account.following())
        return following
    except Exception as ex:
        logging.error(ex)
        return []


def get_rcs(check_accounts: List[str]) -> dict:
    """"
    Calls hive with the `find_rc_accounts` method
    """
    client_rc = get_client(api_type="rc_api")
    try:
        response = client_rc.find_rc_accounts({"accounts": check_accounts})
        return response
    except Exception as ex:
        logging.error(
            f"{client_rc.current_node} {client_rc.api_type} not returning useful results, can't continue"
        )
        raise ex
