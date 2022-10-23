import asyncio
import logging
import os
from datetime import datetime
from itertools import cycle
from tabnanny import check
from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import get_tracking_accounts
from hive_rc_auto.helpers.rc_delegation import (
    RCAccount,
    RCAccType,
    RCManabar,
    get_rc_of_accounts,
)


@st.experimental_memo
def tracking_accounts() -> List[str]:
    ta = get_tracking_accounts()
    return ta


async def fill_rc_list(old_all_rcs: List[RCAccount]) -> List[RCAccount]:
    """
    Returns two lists of RC objects one for the delegating and one for
    the target accounts
    """
    ta = tracking_accounts()

    all_rcs = await get_rc_of_accounts(
        check_accounts=Config.DELEGATING_ACCOUNTS + ta, old_all_rcs=old_all_rcs
    )
    return all_rcs


def rc_guage(rc: RCAccount):
    logging.info(f"reference: {rc.real_mana_percent + rc.delta_percent}")
    logging.info(f"real_mana_percent: {rc.real_mana_percent}")
    logging.info(f"delta_percent: {rc.delta_percent}")
    fig = go.Figure(
        go.Indicator(
            domain={"x": [0, 1], "y": [0, 1]},
            value=rc.real_mana_percent,
            mode="gauge+number+delta",
            title={"text": rc.account},
            delta={"reference": (rc.real_mana_percent + rc.delta_percent)},
            gauge={
                "bar": {"color": "black"},
                "axis": {"range": [0, 100]},
                "steps": [
                    {"range": [0, 10], "color": "red"},
                    {"range": [10, 37], "color": "mediumvioletred"},
                    {"range": [37, 75], "color": "blue"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 10,
                },
            },
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


async def grid(ncol: int = 3, old_all_rcs: List[RCAccount] = None):
    """
    Output a grid <ncol> columns
    """
    all_rcs = await fill_rc_list(old_all_rcs)
    # all_dt = pd.DataFrame([s.__dict__ for s in all_rcs])
    # all_dt = all_dt.set_index("timestamp")
    # st.dataframe(data=all_dt, use_container_width=True)
    st.text("Delegating Accounts")
    cols = st.columns(ncol)
    for i, rc in zip(
        cycle(range(ncol)),
        filter(lambda x: x.delegating == RCAccType.DELEGATING, all_rcs),
    ):
        col = cols[i % ncol]
        # col.metric(
        #     label=rc.account, value=f"{rc.real_mana_percent:.1f} %", delta="1.2 %"
        # )
        col.plotly_chart(rc_guage(rc), use_container_width=True)

    st.text("Target Accounts")
    cols2 = st.columns(ncol)
    for i, rc in zip(
        cycle(range(ncol)),
        filter(
            lambda x: x.delegating == RCAccType.TARGET and x.real_mana_percent < 100,
            all_rcs,
        ),
    ):
        col = cols2[i % ncol]
        col.plotly_chart(rc_guage(rc), use_container_width=True)
        # col.metric(
        #     label=rc.account, value=f"{rc.real_mana_percent:.1f} %", delta="1.2 %"
        # )
    return all_rcs


async def main_loop(old_all_rcs=None):

    logging.info(f"Running at {datetime.now()}")
    st.title("RC Delegations")
    await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)
    logging.info("Running again")



if __name__ == "__main__":
    # debug = False
    # logging.basicConfig(
    #     level=logging.INFO if not debug else logging.DEBUG,
    #     format="%(asctime)s %(levelname)-8s %(module)-14s %(lineno) 5d : %(message)s",
    #     datefmt="%m-%dT%H:%M:%S",
    # )
    logging.info("----------------------------------------")
    logging.info(f"Running at {datetime.now()}")
    logging.info(f"Testnet: {os.getenv('TESTNET')}")
    logging.info("----------------------------------------")
    st.set_page_config(
        page_title="RC Delegation - Auto",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # try:
    asyncio.run(main_loop())
    # except KeyboardInterrupt:
    #     logging.info("Terminated with Ctrl-C")
    # except asyncio.CancelledError:
    #     logging.info("Asyncio cancelled")

    # except Exception as ex:
    #     logging.error(ex.__class__)
