import asyncio
import logging
import os
from datetime import datetime, timedelta
from itertools import cycle
from timeit import default_timer as timer
from typing import Callable, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.rc_delegation import RCAccount, get_mongo_db


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


def build_rc_graph(
    df: pd.DataFrame, df_rc_changes: pd.DataFrame, hive_acc: str
) -> go.Figure:
    start = timer()
    dfa = df[df.account == hive_acc]
    # dfa.resample('10T').mean(numeric_only=True)
    # logging.info(f"Resample {hive_acc} - {timer()-start:.2f}s")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=dfa.age_hours, y=dfa["real_mana_percent"], name="RC %"),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(x=dfa.age_hours, y=dfa["real_mana"], name="RC"),
        secondary_y=False,
    )

    # Very expensive shows each change
    if not df_rc_changes.empty:
        df_rc_change = df_rc_changes[df_rc_changes.account == hive_acc]
        if not df_rc_change.empty:
            for index, row in df_rc_change.iterrows():
                up_down = "down" if row.cut else "up"
                fig.add_vline(
                    x=row.age_hours,
                    line_width=0.6,
                    line_dash="dash",
                    line_color="green",
                )

    # Set x-axis title
    fig.update_xaxes(title_text=f"Age (hours) - {hive_acc}")

    last_reading = dfa.real_mana_percent.iloc[-1]
    fig.update_layout(
        title_text=(
            f"<b>{hive_acc}</b> RC's<br>"
            f"Last reading: <b>{last_reading:.1f}%</b><br>"
            f"Time: {dfa.last_valid_index():%H:%M:%S}"
        )
    )
    # Set y-axes titles
    fig.update_yaxes(title_text="<b>RC %</b>", secondary_y=True)
    fig.update_yaxes(title_text="<b>RC</b>", secondary_y=False)

    yaxes_range_max = dfa["real_mana_percent"].max() + 5
    fig.update_yaxes(range=[0, yaxes_range_max], secondary_y=True)

    fig.update_layout(
        showlegend=True,
    )
    # Position Text
    fig.update_layout(legend_x=0.2, legend_y=0.85)
    fig.update_layout(title_x=0.2, title_y=0.2)

    fig.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})
    fig.update_xaxes(autorange="reversed")
    # fig.show()
    logging.info(f"Time to build graph {hive_acc} - {timer()-start:.4f}s")
    return fig


async def get_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Fetch data from Mongodb returns two dataframes:
    # df -> main data of rc levels
    # df_rc_changes -> data for changes.

    db_rc_ts = get_mongo_db(Config.DB_NAME)
    if st.session_state.hours == "All":
        time_limit = timedelta(weeks=30)
    else:
        time_limit = timedelta(hours=st.session_state.hours)
    earliest_data = datetime.utcnow() - time_limit

    cursor = db_rc_ts.find(
        {"real_mana": {"$ne": None}, "timestamp": {"$gte": earliest_data}}, {"_id": 0}
    )

    data = []
    async for doc in cursor:
        data.append(doc)

    df = pd.DataFrame(data)
    df["age"] = datetime.utcnow() - df.timestamp
    df.set_index("timestamp", inplace=True)
    df["age_hours"] = df["age"].dt.total_seconds() / 3600

    db_rc_ts_deleg = get_mongo_db(Config.DB_NAME_DELEG)
    cursor = db_rc_ts_deleg.find({"timestamp": {"$gte": earliest_data}}, {"_id": 0})
    data = []
    async for doc in cursor:
        data.append(doc)

    df_rc_changes = pd.DataFrame(data)
    if data:
        df_rc_changes["age"] = datetime.utcnow() - df_rc_changes.timestamp
        df_rc_changes.set_index("timestamp", inplace=True)
        df_rc_changes["age_hours"] = df_rc_changes["age"].dt.total_seconds() / 3600

    st.session_state.df = df
    st.session_state.df_rc_changes = df_rc_changes

    return df, df_rc_changes


def hours_selectbox():
    hours_selectbox_options = [4, 8, 24, 72, "All"]
    cols = st.columns(3)
    cols[0].subheader("RC Levels")
    st.session_state.hours = cols[1].selectbox(
        label="Hours",
        options=hours_selectbox_options,
        index=2,
        help="The number of hours of data to show",
        # on_change=st.experimental_rerun(),
    )


async def grid(ncol: int = 2):

    df, df_rc_changes = await get_data()
    df_delegating = df[df["delegating"] == "delegating"]
    del_accounts = df_delegating.account.unique()
    all_accounts = df[df.delegating == "target"].account.unique()
    all_accounts.sort()
    filtered_accounts = []

    for hive_acc in all_accounts:
        dfa = df[df.account == hive_acc]
        if dfa.real_mana_percent.iloc[-1] < 95 and (
            not dfa.delegating.iloc[-1] == "delegating"
        ):
            filtered_accounts.append(hive_acc)

    st.subheader("Delegating Accounts")
    cols = st.columns(ncol)
    for i, hive_acc in zip(
        cycle(range(ncol)),
        del_accounts,
    ):
        col = cols[i % ncol]
        dfa = df[df.account == hive_acc]
        col.plotly_chart(
            build_rc_graph(df, df_rc_changes, hive_acc), use_container_width=True
        )
    st.subheader("Receiving Accounts")
    cols2 = st.columns(ncol)
    for i, hive_acc in zip(
        cycle(range(ncol)),
        filtered_accounts,
    ):
        col = cols2[i % ncol]
        dfa = df[df.account == hive_acc]
        col.plotly_chart(
            build_rc_graph(df, df_rc_changes, hive_acc), use_container_width=True
        )


def run_async(func: Callable, params=None):
    loop = asyncio.get_running_loop()
    asyncio.run_coroutine_threadsafe(func(params), loop=loop)


async def rerun_after_data_update():
    await asyncio.sleep(Config.UPDATE_FREQUENCY_SECS)
    # await asyncio.sleep(3)
    logging.info("Re-running for new data")
    st.experimental_rerun()


async def main_loop():
    logging.info(f"Running at {datetime.now()}")
    if "hours" not in st.session_state:
        st.session_state.hours = 24
    hours_selectbox()
    await grid(ncol=3)

    # await rerun_after_data_update()


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
    st.sidebar.markdown("# RC Overview 📈")
    # try:
    asyncio.run(main_loop())
    # except KeyboardInterrupt:
    #     logging.info("Terminated with Ctrl-C")
    # except asyncio.CancelledError:
    #     logging.info("Asyncio cancelled")

    # except Exception as ex:
    #     logging.error(ex.__class__)
