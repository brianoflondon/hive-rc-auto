import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pymongo import MongoClient

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)


def all_trans_by_account():
    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            {"$match": {"metadata.posting_auth": {"$ne": "podping.test"}}},
            {
                "$group": {
                    "_id": {
                        "account": "$metadata.posting_auth",
                        "timestamp": {
                            "$dateTrunc": {
                                "date": "$timestamp",
                                "unit": time_frame,
                                "timezone": "Asia/Jerusalem",
                            }
                        },
                    },
                    "timestamp": {"$first": "$timestamp"},
                    "account": {"$first": "$metadata.posting_auth"},
                    "avg_size": {"$avg": "$json_size"},
                    "total_size": {"$sum": "$json_size"},
                    "total_podpings": {"$sum": 1},
                    "total_iris": {"$sum": "$num_iris"},
                }
            },
            {"$sort": {"_id.timestamp": -1}},
        ]
    )
    return result


def all_trans_no_account():
    result_no_account = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            {"$match": {"metadata.posting_auth": {"$ne": "podping.test"}}},
            {
                "$group": {
                    "_id": {
                        "timestamp": {
                            "$dateTrunc": {
                                "date": "$timestamp",
                                "unit": time_frame,
                                "timezone": "Asia/Jerusalem",
                            }
                        }
                    },
                    "timestamp": {"$first": "$timestamp"},
                    "avg_size": {"$avg": "$json_size"},
                    "total_size": {"$sum": "$json_size"},
                    "total_podpings": {"$sum": 1},
                    "total_iris": {"$sum": "$num_iris"},
                }
            },
            {"$sort": {"_id.timestamp": -1}},
        ]
    )
    return result_no_account


def hour_trans_by_account(time_limit: datetime, time_frame: str):
    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            {
                "$match": {
                    "timestamp": {"$gt": time_limit},
                }
            },
            {
                "$group": {
                    "_id": {
                        "account": "$metadata.posting_auth",
                        "timestamp": {
                            "$dateTrunc": {
                                "date": "$timestamp",
                                "unit": time_frame,
                                "timezone": "Asia/Jerusalem",
                            }
                        },
                    },
                    "timestamp": {"$first": "$timestamp"},
                    "account": {"$first": "$metadata.posting_auth"},
                    "avg_size": {"$avg": "$json_size"},
                    "total_size": {"$sum": "$json_size"},
                    "total_podpings": {"$sum": 1},
                    "total_iris": {"$sum": "$num_iris"},
                }
            },
            {"$sort": {"_id.timestamp": -1}},
        ]
    )
    return result


def hour_trans_no_account(time_limit: datetime, time_frame: str):
    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            {
                "$match": {
                    "timestamp": {"$gt": time_limit},
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
                            }
                        }
                    },
                    "timestamp": {"$first": "$timestamp"},
                    "avg_size": {"$avg": "$json_size"},
                    "total_size": {"$sum": "$json_size"},
                    "total_podpings": {"$sum": 1},
                    "total_iris": {"$sum": "$num_iris"},
                }
            },
            {"$sort": {"_id.timestamp": -1}},
        ]
    )
    return result


st.set_page_config(layout="wide")
time_frame = "hour"
result = all_trans_by_account()
df = pd.DataFrame(result)
df.set_index("timestamp", inplace=True)

df_no_account = pd.DataFrame(all_trans_no_account())
df_no_account.set_index("timestamp", inplace=True)

all_accounts = df.account.unique()
all_accounts.sort()
fig = make_subplots(specs=[[{"secondary_y": True}]])
for account in all_accounts:
    fig.add_trace(
        go.Scatter(
            x=df[df.account == account].index,
            y=df[df.account == account].total_iris,
            name=account,
            mode="markers",
        ),
        secondary_y=True,
    )
fig.add_trace(
    go.Scatter(x=df_no_account.index, y=df_no_account.total_iris, name="All Iris")
)

fig.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="right", x=0.9)
)
fig.update_layout(title_x=0.2, title_y=0.2)
fig.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})

end_range = datetime.utcnow() + timedelta(hours=0.5)
start_range = end_range - timedelta(days=30)
fig.update_layout(xaxis=dict(range=[start_range,end_range]))

st.title("IRIs Sent per Hour by each account")
st.plotly_chart(fig, use_container_width=True)

number_hours = 4

time_frame = "minute"
time_limit = datetime.utcnow() - timedelta(hours=number_hours)
result = hour_trans_by_account(time_limit=time_limit, time_frame=time_frame)
df_hour = pd.DataFrame(result)
df_hour.set_index("timestamp", inplace=True)

df_hour_no_account = pd.DataFrame(hour_trans_no_account(time_limit, time_frame))
df_hour_no_account.set_index("timestamp", inplace=True)

all_accounts = df_hour.account.unique()
all_accounts.sort()
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
for account in all_accounts:
    fig2.add_trace(
        go.Scatter(
            x=df_hour[df_hour.account == account].index,
            y=df_hour[df_hour.account == account].total_iris,
            name=account,
            mode="markers",
            marker=dict(size=10 + df_hour[df_hour.account == account].total_size / 512),
        ),
        secondary_y=True,
    )
fig2.add_trace(
    go.Scatter(
        x=df_hour_no_account.index, y=df_hour_no_account.total_iris, name="All Iris"
    )
)

fig2.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="right", x=0.9)
)
fig2.update_layout(title_x=0.2, title_y=0.2)
fig2.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})
st.title(f"Last {number_hours} hours of IRIs per minute by Accounts")
st.plotly_chart(fig2, use_container_width=True)
