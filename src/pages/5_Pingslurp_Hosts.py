import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

from hive_rc_auto.helpers.markdown.static_text import import_text

ALL_MARKDOWN = import_text()

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)

time_frame = "minute"
bin_size = 60
start_date = datetime.utcnow() - timedelta(hours=72)
end_data = datetime.utcnow() - timedelta(hours=0)
result = CLIENT["pingslurp"]["hosts_ts"].aggregate(
    [
        {
            "$match": {
                "$and": [
                    {"timestamp": {"$gt": start_date}},
                    {"timestamp": {"$lt": end_data}},
                ]
            }
        },
        {
            "$group": {
                "_id": {
                    "host": "$metadata.host",
                    "timestamp": {
                        "$dateTrunc": {
                            "date": "$timestamp",
                            "unit": time_frame,
                            "timezone": "Asia/Jerusalem",
                            "binSize": bin_size,
                        }
                    },
                },
                "timestamp": {"$first": "$timestamp"},
                "host": {"$first": "$metadata.host"},
                "total_iris": {"$sum": 1},
            }
        },
        {
            "$sort": {
                "_id.timestamp": -1,
            }
        },
    ]
)

result_total = CLIENT["pingslurp"]["hosts_ts"].aggregate(
    [
        {
            "$match": {
                "$and": [
                    {"timestamp": {"$gt": start_date}},
                    {"timestamp": {"$lt": end_data}},
                ]
            }
        },
        {
            "$group": {
                "_id": {
                    "timestamp": {
                        "$dateTrunc": {
                            "date": "$timestamp",
                            "unit": time_frame,
                            "timezone": "Asia/Jerusalem",
                            "binSize": bin_size,
                        }
                    }
                },
                "timestamp": {"$first": "$timestamp"},
                "total_iris": {"$sum": 1},
            }
        },
        {
            "$sort": {
                "_id.timestamp": -1,
            }
        },
    ]
)

df = pd.DataFrame(result)
df.set_index(["timestamp"], inplace=True)
df_total = pd.DataFrame(result_total)
df_total.set_index(["timestamp"], inplace=True)

df_total["cum_iris"] = df_total["total_iris"].cumsum()
df_total["avg4H"] = df_total["total_iris"].rolling(window="4H", center=True).mean()
df_total["avg8H"] = df_total["total_iris"].rolling(window="8H", center=True).mean()
df_total["avg24H"] = df_total["total_iris"].rolling(window="24H", center=True).mean()

result_recent_ping = CLIENT["pingslurp"]["hosts_ts"].aggregate(
    [
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$metadata.host", "timestamp": {"$first": "$timestamp"}}},
    ]
)
df_recent_ping = pd.DataFrame(result_recent_ping)
df_recent_ping["age"] = datetime.utcnow() - df_recent_ping["timestamp"]
df_recent_ping.rename(columns={"_id": "host"}, inplace=True)
df_recent_ping.set_index("timestamp", inplace=True)
df_recent_ping.sort_index(inplace=True, ascending=False)

hosts_sorted = df.host.unique()

for host in df.host.unique():
    df.loc[df.host == host, "cum_iris"] = df[df.host == host]["total_iris"].cumsum()
    df.loc[df.host == host, "avg4H"] = (
        df[df.host == host]["total_iris"].rolling(window="4H", center=True).mean()
    )
    df.loc[df.host == host, "avg8H"] = (
        df[df.host == host]["total_iris"].rolling(window="8H", center=True).mean()
    )
    df.loc[df.host == host, "avg24H"] = (
        df[df.host == host]["total_iris"].rolling(window="24H", center=True).mean()
    )


summary = []

for host in hosts_sorted:
    dfa = df.loc[df.host == host]
    if not dfa.empty and len(dfa) > 1:
        try:
            logging.info(dfa["host"].iloc[0])
            summary.append(
                {
                    "host": dfa["host"].iloc[0],
                    "hour_0": dfa["total_iris"].iloc[0],
                    "hour_1": dfa["total_iris"].iloc[1],
                    "hour_2": dfa["total_iris"].iloc[2],
                    "avg4H": dfa["avg4H"].iloc[0],
                    "avg8H": dfa["avg8H"].iloc[0],
                    "avg24H": dfa["avg24H"].iloc[0],
                    "max_val": dfa["total_iris"].max(),
                    "min_val": dfa["total_iris"].min(),
                }
            )
        except IndexError:
            logging.warning(f"IndexError with {dfa['host'].iloc[0]}")

summary.append(
    {
        "host": "Total",
        "hour_0": df_total["total_iris"].iloc[0],
        "hour_1": df_total["total_iris"].iloc[1],
        "hour_2": df_total["total_iris"].iloc[2],
        "avg4H": df_total["avg4H"].iloc[0],
        "avg8H": df_total["avg8H"].iloc[0],
        "avg24H": df_total["avg24H"].iloc[0],
        "max_val": df_total["total_iris"].max(),
        "min_val": df_total["total_iris"].min(),
    }
)

df_summary = pd.DataFrame(data=summary)


def gauge(host: str):
    value = int(df_summary[df_summary.host == host].hour_1)
    reference = int(df_summary[df_summary.host == host].hour_2)
    min_val = int(df_summary[df_summary.host == host].min_val)
    max_val = int(df_summary[df_summary.host == host].max_val)
    avg4H = int(df_summary[df_summary.host == host].avg4H)
    avg8H = int(df_summary[df_summary.host == host].avg8H)
    avg24H = int(df_summary[df_summary.host == host].avg24H)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            delta={"reference": reference},
            domain={"x": [0, 1], "y": [0, 1]},
            # title = {'text': f"{host}"},
            gauge={
                "axis": {"range": [0, max_val]},
                "steps": [
                    {"range": [0, min_val], "color": "red"},
                    {"range": [min_val, avg8H], "color": "lightgray"},
                ],
                "threshold": {
                    "line": {"color": "blue", "width": 4},
                    "thickness": 0.75,
                    "value": avg8H,
                },
            },
        )
    )

    fig.update_layout(margin=dict(b=10, t=20, l=15, r=15, autoexpand=True))
    # fig.update_layout(title=dict(font=dict(size=20)))
    fig.update_layout(height=150)
    # fig.update_layout(title_text=host)
    return fig


st.set_page_config(
    page_title="Pingslurp Hosts",
    page_icon="pages/android-chrome-512x512.png",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items=None,
)

top_cols = st.columns(2)
top_cols[0].markdown("# Pingslurp Health")
st.sidebar.markdown(ALL_MARKDOWN["pingslurp_hosts"])

ncol = 5
top_cols[0].subheader("Total Iris sent in the last Hour")
fig = gauge("Total")
top_cols[1].plotly_chart(fig, use_container_width=True)
top_cols[1].subheader("Total")
st.sidebar.plotly_chart(fig, use_container_width=True)
st.sidebar.subheader("Total")
cols = st.columns(ncol)


def seconds_only(time_delta: timedelta) -> timedelta:
    """Strip out microseconds"""
    return time_delta - timedelta(microseconds=time_delta.microseconds)


hosts = df_summary.sort_values(by="hour_1", ascending=False)["host"]
for i, host in enumerate(hosts.iloc[1:]):
    fig = gauge(host=host)
    cols[i % ncol].plotly_chart(fig, use_container_width=True)
    last_ping = df_recent_ping[df_recent_ping["host"] == host].age.iloc[0]
    cols[i % ncol].subheader(f"{host}")
    cols[i % ncol].text(f"Last Ping: {seconds_only(last_ping)}")


fig_graph = go.Figure()
fig_graph.add_trace(
    go.Scatter(x=df_total.index, y=df_total.avg8H, mode="lines", name="8hr Moving Avg")
)
fig_graph.add_trace(
    go.Scatter(
        x=df_total.index, y=df_total.total_iris, mode="markers", name="Total IRIs/hour"
    )
)

# df_recent_ping.set_index("timestamp", inplace=True)
# for index, ping in df_recent_ping.iterrows():
#     fig.add_vline(
#         x= 0,
#         line_width=3,
#         line_dash="dash",
#         line_color="green",
#         annotation_text=ping['host'],
#         annotation_position="top right",
#     )


st.plotly_chart(fig_graph, use_container_width=True)

st.subheader("Most recent Podpings per major host")
for index, ping in df_recent_ping.iterrows():
    st.markdown(f"{ping.host:>20} - Last Podping: {ping.age}")

# st.dataframe(df)
# st.dataframe(df_recent_ping[['host','timestamp']])
st.dataframe(df_summary)
