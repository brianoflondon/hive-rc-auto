import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pymongo import MongoClient

from hive_rc_auto.helpers.markdown.static_text import import_text

ALL_MARKDOWN = import_text()

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)


def all_trans_by_account():
    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            # {"$match": {"metadata.posting_auth": {"$ne": "podping.test"}}},
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
            # {"$match": {"metadata.posting_auth": {"$ne": "podping.test"}}},
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


metrics = {
    "Total IRIs": "total_iris",
    "Total Podpings": "total_podpings",
    "Total Size (Mb)": "total_size_mb",
    "Average Size (Kb)": "avg_size",
}


st.set_page_config(layout="wide")
st.session_state.metric = st.sidebar.selectbox(
    label="Metric", options=metrics.keys(), help="Metric to show"
)
st.sidebar.markdown(ALL_MARKDOWN["pingslurp_accounts"])
choice = st.session_state.metric

metric = metrics[choice]
metric_desc = choice

time_frame = "hour"

result = all_trans_by_account()
df = pd.DataFrame(result)
df.set_index("timestamp", inplace=True)
df["total_size_mb"] = df["total_size"] / (1024 * 1024)

df_no_account = pd.DataFrame(all_trans_no_account())
df_no_account.set_index("timestamp", inplace=True)
df_no_account["total_size_mb"] = df_no_account["total_size"] / (1024 * 1024)

all_accounts = df.account.unique()
all_accounts.sort()
fig = make_subplots(specs=[[{"secondary_y": True}]])
for account in all_accounts:
    fig.add_trace(
        go.Scatter(
            x=df[df.account == account].index,
            y=df[df.account == account][metric],
            name=account,
            mode="markers",
            marker=dict(size=5 + df[df.account == account].total_size / 2 ** 14),
        ),
        secondary_y=True,
    )
fig.add_trace(
    go.Scatter(x=df_no_account.index, y=df_no_account[metric], name=metric_desc)
)

fig.add_trace(
    go.Scatter(
        x=df_no_account.index,
        y=df_no_account[metric].rolling(24).mean(),
        name=f"{metric_desc} (24H avg)",
    )
)

# fig.update_layout(
#     legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="right", x=0.9)
# )
fig.update_layout(margin={"autoexpand": True, "b": 20, "t": 0, "l": 0, "r": 0})
fig.update_yaxes(title_text=f"{metric_desc}", secondary_y=False, showgrid=False)
fig.update_yaxes(
    title_text=f"{metric_desc} by account", secondary_y=True, showgrid=False
)

fig.update_xaxes(showspikes=True)
fig.update_yaxes(showspikes=True)
# Grid lines
# fig.update_xaxes(gridwidth=0.1, gridcolor="LightGrey")
# fig.update_yaxes(showline=False, gridwidth=0.1)
# fig.update_yaxes(gridwidth=0.1, secondary_y=True)

fig.update_layout(title_x=0.05, title_y=0.95)
fig.update_layout(title_text=f"{metric_desc} Sent per Hour by each account")

end_range = datetime.utcnow() + timedelta(hours=0.5)
start_range = end_range - timedelta(days=30)
fig.update_layout(xaxis=dict(range=[start_range, end_range]))


st.title(body=f"{metric_desc} Sent per Hour by each account")
st.plotly_chart(fig, use_container_width=True)

number_hours = 4

time_frame = "minute"
time_limit = datetime.utcnow() - timedelta(hours=number_hours)
result = hour_trans_by_account(time_limit=time_limit, time_frame=time_frame)
df_hour = pd.DataFrame(result)
df_hour.set_index("timestamp", inplace=True)
df_hour["total_size_mb"] = df_hour["total_size"] / (1024 * 1024)

df_hour_no_account = pd.DataFrame(hour_trans_no_account(time_limit, time_frame))
df_hour_no_account.set_index("timestamp", inplace=True)
df_hour_no_account["total_size_mb"] = df_hour_no_account["total_size"] / (1024 * 1024)

all_accounts = df_hour.account.unique()
all_accounts.sort()
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
for account in all_accounts:
    fig2.add_trace(
        go.Scatter(
            x=df_hour[df_hour.account == account].index,
            y=df_hour[df_hour.account == account][metric],
            name=account,
            mode="markers",
            marker=dict(size=10 + df_hour[df_hour.account == account].total_size / 256),
        ),
        secondary_y=True,
    )
fig2.add_trace(
    go.Scatter(
        x=df_hour_no_account.index, y=df_hour_no_account[metric], name=metric_desc
    )
)
fig2.add_trace(
    go.Scatter(
        x=df_hour_no_account.index,
        y=df_hour_no_account[metric].rolling('1H').mean(),
        name=f"{metric_desc} (1hr Avg)",
    )
)


# fig2.update_layout(
#     legend=dict(orientation="v", yanchor="top", y=0, xanchor="auto", x=1.15)
# )
fig2.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})

fig2.update_yaxes(title_text=metric_desc, secondary_y=False, showgrid=False)
fig2.update_layout(title_x=0.05, title_y=0.95)

fig2.update_yaxes(
    title_text=f"{metric_desc} by account", secondary_y=True, showgrid=False
)
fig2.update_layout(
    title_text=f"Last {number_hours} hours of {metric_desc} per minute by Accounts"
)

fig2.update_xaxes(showspikes=True)
fig2.update_yaxes(showspikes=True)
st.title(f"Last {number_hours} hours of {metric_desc} per minute by Accounts")
st.plotly_chart(fig2, use_container_width=True)

st.dataframe(df_hour.groupby("account")[metric].describe())
