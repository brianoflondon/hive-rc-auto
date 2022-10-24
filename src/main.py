import asyncio
import logging
import os
from datetime import datetime
from itertools import cycle
from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import get_tracking_accounts
from hive_rc_auto.helpers.rc_delegation import (
    RCAccount,
    RCAccType,
    RCAllData,
    RCListOfAccounts,
    RCManabar,
    get_mongo_db,
    get_rc_of_accounts,
    get_utc_now_timestamp,
)


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


async def grid(ncol: int = 2):
    """
    Output a grid <ncol> columns
    """
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


def build_rc_graph(
    df: pd.DataFrame, df_rc_changes: pd.DataFrame, hive_acc: str
) -> go.Figure:
    dfa = df[df.account == hive_acc]
    df_rc_change = df_rc_changes[df_rc_changes.account == hive_acc]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=dfa.age_hours, y=dfa["real_mana_percent"], name="RC %"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=dfa.age_hours, y=dfa["real_mana"], name="RC"),
        secondary_y=True,
    )

    for index, row in df_rc_change.iterrows():
        up_down = "down" if row.cut else "up"
        fig.add_vline(x=row.age_hours, line_width=0.6, line_dash="dash", line_color="green")

    # Set x-axis title
    fig.update_xaxes(title_text=f"Age (hours) - {hive_acc}")

    fig.update_layout(title_text=f"<b>{hive_acc}</b> Resource Credits")
    # Set y-axes titles
    fig.update_yaxes(title_text="<b>RC %</b>", secondary_y=False)
    fig.update_yaxes(title_text="<b>RC</b>", secondary_y=True)

    yaxes_range_max = dfa['real_mana_percent'].max() + 5
    fig.update_yaxes(range=[0, yaxes_range_max], secondary_y=False)

    fig.update_layout(showlegend=True,)
    fig.update_layout(legend_x=0.85, legend_y=0.85)
    fig.update_xaxes(autorange="reversed")
    # fig.show()
    return fig


async def get_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch data from Mongodb"""
    db_name = "rc_history_testnet" if Config.TESTNET else "rc_history"
    db_rc_history = get_mongo_db(db_name)
    cursor = db_rc_history.find({"real_mana": {"$ne": None}}, {"_id": 0})

    data = []
    async for doc in cursor:
        data.append(doc)

    df = pd.DataFrame(data)
    df["age"] = datetime.utcnow() - df.timestamp
    df.set_index("timestamp", inplace=True)
    df["age_hours"] = df['age'].dt.total_seconds()/3600


    cursor = db_rc_history.find({"real_mana": None}, {"_id": 0})
    data = []
    async for doc in cursor:
        data.append(doc)

    df_rc_changes = pd.DataFrame(data)
    df_rc_changes["age"] = datetime.utcnow() - df_rc_changes.timestamp
    df_rc_changes.set_index("timestamp", inplace=True)
    df_rc_changes["age_hours"] = df_rc_changes['age'].dt.total_seconds()/3600
    return df, df_rc_changes


async def main_loop(old_all_rcs=None):

    logging.info(f"Running at {datetime.now()}")
    df, df_rc_changes = await get_data()
    all_accounts = df.account.unique()
    all_accounts.sort()
    st.title("RC Levels")
    for hive_acc in all_accounts:
        dfa = df[df.account == hive_acc]
        df_rc_change = df_rc_changes[df_rc_changes.account == hive_acc]

        if dfa.real_mana_percent.iloc[-1] < 95:
            st.plotly_chart(build_rc_graph(df, df_rc_changes, hive_acc))

    await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)
    logging.info("Running again")


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
