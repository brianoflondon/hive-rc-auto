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
from pymongo import MongoClient
from streamlit_autorefresh import st_autorefresh

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.markdown.static_text import import_text
from hive_rc_auto.helpers.pingslurp_accounts import (
    dataframe_all_transactions_by_account,
)
from hive_rc_auto.helpers.rc_delegation import RCAccount

ALL_MARKDOWN = import_text()


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
    df: pd.DataFrame, df_rc_changes: pd.DataFrame, hive_acc: str, df_size: pd.DataFrame = pd.DataFrame()
) -> go.Figure:
    start = timer()
    dfa = df[df.account == hive_acc]
    # dfa.resample('10T').mean(numeric_only=True)
    # logging.info(f"Resample {hive_acc} - {timer()-start:.2f}s")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=dfa.age_hours,
            y=dfa["real_mana_percent"],
            name="RC %",
            text=[f"{ts:%d %H:%M}" for ts in dfa.index],
            hovertemplate="-%{x:.1f} hours<br>%{text}" + "<br>%{y:,.1f}%",
            line = dict(color='blue'),
        ),
        secondary_y=True,
    )
    if st.session_state.show_size:
        if not df_size.empty:
            df_size["age_hours"] = (datetime.utcnow() - df_size.index).total_seconds() / 3600
            df_size_a = df_size[df_size.account == hive_acc]
            if not df_size_a.empty:
                fig.update_yaxes(title_text="<b>Bytes/min</b>", secondary_y=False)
                fig.add_trace(
                    go.Scatter(
                        x=df_size_a.age_hours,
                        y=df_size_a["total_size"].rolling('4H', closed='neither').mean(),
                        name="Bytes/min",
                        text=[f"{ts:%d %H:%M}" for ts in df_size_a.index],
                        hovertemplate="-%{x:.1f} hours<br>%{text}" + "<br>%{y:,.0f} bytes",
                        line = dict(color='lightgreen'),
                    ),
                    secondary_y=False,
                )
    if not st.session_state.show_size or df_size.empty:
        fig.update_yaxes(title_text="<b>RC</b>", secondary_y=False)
        fig.add_trace(
            go.Scatter(
                x=dfa.age_hours,
                y=dfa["real_mana"],
                name="RC",
                text=[f"{ts:%d %H:%M}" for ts in dfa.index],
                hovertemplate="-%{x:.1f} hours<br>%{text}" + "<br>%{y:,.3s}",
                line = dict(color='red'),
            ),
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


def get_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Fetch data from Mongodb returns two dataframes:
    # df -> main data of rc levels
    # df_rc_changes -> data for changes.
    DB_CONNECTION = os.getenv("DB_CONNECTION")
    CLIENT = MongoClient(DB_CONNECTION)
    db_rc_ts = CLIENT["rc_podping"][Config.DB_NAME]

    if st.session_state.hours == "All":
        time_limit = timedelta(weeks=4)
    else:
        time_limit = timedelta(hours=st.session_state.hours)
    earliest_data = datetime.utcnow() - time_limit

    result = db_rc_ts.find(
        {"real_mana": {"$ne": None}, "timestamp": {"$gte": earliest_data}}, {"_id": 0}
    )

    df = pd.DataFrame(result)
    if not df.empty:
        df["age"] = datetime.utcnow() - df.timestamp
        df.set_index("timestamp", inplace=True)
        df["age_hours"] = df["age"].dt.total_seconds() / 3600

        db_rc_ts_deleg = CLIENT["rc_podping"][Config.DB_NAME_DELEG]
        result2 = db_rc_ts_deleg.find(
            {"timestamp": {"$gte": earliest_data}}, {"_id": 0}
        )

        df_rc_changes = pd.DataFrame(result2)
        if not df_rc_changes.empty:
            df_rc_changes["age"] = datetime.utcnow() - df_rc_changes.timestamp
            df_rc_changes.set_index("timestamp", inplace=True)
            df_rc_changes["age_hours"] = df_rc_changes["age"].dt.total_seconds() / 3600

        st.session_state.df = df
        st.session_state.df_rc_changes = df_rc_changes

        return df, df_rc_changes


def hours_selectbox():
    hours_selectbox_options = [4, 8, 24, 72, "All"]
    st.session_state.hours = st.sidebar.selectbox(
        label="Hours",
        options=hours_selectbox_options,
        index=2,
        help="The number of hours of data to show",
        # on_change=st.experimental_rerun(),
    )

def size_selectbox():
    size_selectbox_options = {
        "Show Data bytes/min": True,
        "Show RC (vests)": False
    }
    show_size_choice = st.sidebar.selectbox(
        label="Show Size/RC vests",
        options=size_selectbox_options.keys(),
        index=0,
        help="Show either the amount of data written to Hive bytes per hour or Absolute RC level in vests",
    )
    st.session_state.show_size = size_selectbox_options[show_size_choice]


def grid(ncol: int = 2):

    df, df_rc_changes = get_data()
    hours = st.session_state.hours
    if hours == "All":
        hours = int(4*24*7*4)
    time_range = {
        "$match": {
            "timestamp": {
                "$gt": datetime.utcnow() - timedelta(hours=hours)
            }
        }
    }
    livetest_filter = {"$match": {}}

    df_size = dataframe_all_transactions_by_account(
        time_frame="minute", time_range=time_range, livetest_filter=livetest_filter
    )
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
            build_rc_graph(df, df_rc_changes, hive_acc, df_size), use_container_width=True
        )


def main_loop():
    logging.info(f"Running at {datetime.now()}")
    if "hours" not in st.session_state:
        st.session_state.hours = 24
    grid(ncol=3)
    st.markdown(ALL_MARKDOWN["rc_overview"])

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
        page_icon="pages/android-chrome-512x512.png",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    cols = st.columns(3)
    cols[0].subheader("RC Levels")
    hours_selectbox()
    size_selectbox()
    st.sidebar.markdown(ALL_MARKDOWN["rc_overview"])
    # try:
    main_loop()

    df = st.session_state.df_rc_changes
    df.sort_values(by="age", ascending=True, inplace=True)
    if not df.empty:
        df["link"] = f"[Link](https://hive.ausbit.dev/tx/" + df["trx_id"] + ")"
        df = df.drop(
            ["deleg", "age", "trx_num", "trx_id", "block_num", "account"], axis=1
        )
        mkd = df.to_markdown()
        st.markdown(mkd)
        st.dataframe(df, use_container_width=True)
