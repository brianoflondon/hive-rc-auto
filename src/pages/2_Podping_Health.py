import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pymongo import MongoClient

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)

st.set_page_config(layout="wide")
st.markdown("# Podping Health")
st.sidebar.markdown("# Podping Health")
time_frame = "minute"
start_date = datetime.utcnow() - timedelta(hours=72)
result = CLIENT["pingslurp"]["hosts_ts"].aggregate(
    [
        {
            "$match": {
                "timestamp": {"$gt": start_date},
                # 'metadata.host': 'Transistor'
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
                            "binSize": 60,
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
                "timestamp": {"$gt": start_date},
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
                            "binSize": 60,
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

hosts_sorted = df.host.unique()
hosts_sorted.sort(kind="stable")

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
    value = int(df_summary[df_summary.host == host].hour_0)
    reference = int(df_summary[df_summary.host == host].hour_1)
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

    fig.update_layout(margin=dict(b=10, t=20, l=5, r=5))
    fig.update_layout(title=dict(font=dict(size=20)))
    fig.update_layout(height=150)
    # fig.update_layout(title_text=host)
    return fig

ncol = 6
st.subheader("Total Iris sent in the last Hour")
cols = st.columns(ncol)
# cols[0].plotly_chart(gauge("Total"), use_container_width=True)


for i, host in enumerate(["Total", *hosts_sorted]):
    fig = gauge(host=host)
    cols[i % ncol].plotly_chart(fig, use_container_width=True)
    cols[i % ncol].subheader(host)


# st.dataframe(df)
# st.dataframe(df_total)
