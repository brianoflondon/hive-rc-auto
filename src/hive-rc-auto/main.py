import asyncio
import logging
import os
from datetime import datetime
from itertools import cycle
from typing import List

import numpy as np
import pandas as pd
import streamlit as st

from helpers.config import Config
from helpers.hive_calls import tracking_accounts
from helpers.rc_delegation import RCManabar


async def get_tracking_accounts() -> List[str]:
    return tracking_accounts()

async def grid(ncol: int = 5):
    """
    Output a grid <ncol> columns
    """
    ncol = 5
    cols = st.columns(ncol)
    tracking_accounts = await get_tracking_accounts()
    st.text(Config.DELEGATING_ACCOUNTS)
    for i, acc in zip(cycle(range(ncol)), Config.DELEGATING_ACCOUNTS):
        col = cols[i % 5]
        col.metric(label=acc, value="23 %", delta="1.2 %")

    cols = st.columns(ncol)
    st.text(tracking_accounts)
    for i, acc in zip(cycle(range(ncol)), tracking_accounts):
        col = cols[i % 5]
        col.metric(label=acc, value="23 %", delta="1.2 %")



async def main_loop():
    logging.info(Config.DELEGATING_ACCOUNTS)

    st.set_page_config(
        page_title="RC Delegation - Auto",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("RC Delegations")
    await grid()
    # for acc in tracking_accounts:
    #     st.metric(label=acc, value="23 %", delta="1.2 %")


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

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Terminated with Ctrl-C")
    except asyncio.CancelledError:
        logging.info("Asyncio cancelled")

    except Exception as ex:
        logging.error(ex.__class__)
