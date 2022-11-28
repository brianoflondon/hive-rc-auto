import logging
import os
import re
from datetime import datetime, timedelta
from timeit import default_timer as timer

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pymongo import MongoClient

from hive_rc_auto.helpers.markdown.static_text import import_text

ALL_MARKDOWN = import_text()

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)


exclude_livetest = {"$match": {"metadata.id": re.compile(r"pp_.*")}}
livetest_only = {"$match": {"metadata.id": re.compile(r"pply_.*")}}
include_livetest = {}
livetest_filter = livetest_only
start = timer()

def all_trans_by_account():
    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            st.session_state.time_range,
            st.session_state.livetest_filter,
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
            st.session_state.time_range,
            st.session_state.livetest_filter,
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
            st.session_state.livetest_filter,
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
            st.session_state.livetest_filter,
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
    "Total Size (Kb)": "total_size_kb",
    "Average Size (b)": "avg_size",
}


livetest_filter = {
    "Exclude Live Tests": {"$match": {"metadata.id": re.compile(r"pp_.*")}},
    "Include Live Tests": {"$match": {}},
    "Only Live Tests": {"$match": {"metadata.id": re.compile(r"pplt_.*")}},
}

time_range = {
    "30 Days": {"$match": {"timestamp": {"$gt": datetime.utcnow() - timedelta(days=30)}}},
    "60 Days": {"$match": {"timestamp": {"$gt": datetime.utcnow() - timedelta(days=60)}}},
    "90 Days": {"$match": {"timestamp": {"$gt": datetime.utcnow() - timedelta(days=90)}}},
}
logging.info(f"Loading pingslurp_accounts")
st.set_page_config(page_title="Podpings by Accounts", page_icon="android-chrome-512x512.png", layout="wide", initial_sidebar_state="auto", menu_items=None)

st.session_state.metric = st.sidebar.selectbox(
    label="Metric", options=metrics.keys(), help="Metric to show"
)
st.session_state.livetest_choice = st.sidebar.selectbox(
    label="Live Tests",
    options=livetest_filter.keys(),
    index=1,
    help=(
        "Show/Hide Live Tests. "
        "Some fake podpings are sent out during testing, "
        "these are usually hidden but can be shown with this option."
    ),
)

st.session_state.livetest_filter = livetest_filter[st.session_state.livetest_choice]

st.session_state.time_range_choice = st.sidebar.selectbox(
    label="Time Range",
    options=time_range.keys()
)
st.session_state.time_range =time_range[st.session_state.time_range_choice]

st.sidebar.markdown(ALL_MARKDOWN["pingslurp_accounts"])
choice = st.session_state.metric


metric = metrics[choice]
metric_desc = choice

time_frame = "hour"

result = all_trans_by_account()
df = pd.DataFrame(result)
st.title(body=f"{metric_desc} Sent per Hour by each account")
if df.empty:
    st.markdown(f"## No data")

else:
    df.set_index("timestamp", inplace=True)
    df["total_size_kb"] = df["total_size"] / (1024 * 1)

    df_no_account = pd.DataFrame(all_trans_no_account())
    df_no_account.set_index("timestamp", inplace=True)
    df_no_account["total_size_kb"] = df_no_account["total_size"] / (1024 * 1)

    all_accounts_desc = df.groupby('account')[metric].describe().sort_values(by='mean', ascending=False)
    all_accounts = all_accounts_desc.index
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    logging.info(f"Data loaded for fig 1: {timer() - start}")
    for account in all_accounts:
        fig.add_trace(
            go.Scatter(
                x=df[df.account == account].index,
                y=df[df.account == account][metric],
                name=account,
                text=df[df.account == account]["account"],
                mode="markers",
                marker=dict(size=5 + df[df.account == account].total_size / 2 ** 14),
                hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
            ),
            secondary_y=True,
        )

    fig.update_layout(hoverlabel=dict(font_size=12, font_family="Rockwell"))
    fig.add_trace(
        go.Scatter(
            x=df_no_account.index,
            y=df_no_account[metric],
            name=metric_desc,
            text=[f"{metric_desc}" for _ in df_no_account.index],
            hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_no_account.index[::-1],
            y=df_no_account[metric][::-1].rolling(24).mean(),
            name=f"{metric_desc} (24H avg)",
            text=[f"{metric_desc} (24H avg)" for _ in df_no_account.index],
            hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
        )
    )

    # fig.update_layout(
    #     legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="right", x=0.9)
    # )
    # fig.update_layout(legend=dict(yanchor="top", y=0.1))
    fig.update_layout(margin={"autoexpand": True, "b": 25, "t": 25, "l": 5, "r": 5})
    fig.update_yaxes(title_text=f"{metric_desc}", secondary_y=False, showgrid=False)
    fig.update_yaxes(
        title_text=f"{metric_desc} by account", secondary_y=True, showgrid=False
    )

    fig.update_xaxes(showspikes=True)
    fig.update_yaxes(showspikes=True)
    # Grid lines
    fig.update_xaxes(gridwidth=0.1, gridcolor="LightGrey")
    fig.update_yaxes(showline=False, gridwidth=0.1)
    fig.update_yaxes(gridwidth=0.1, secondary_y=True)

    fig.update_layout(title_x=0.05, title_y=0.9)
    fig.update_layout(title_text=f"{metric_desc} Sent per Hour by each account")

    end_range = datetime.utcnow() + timedelta(hours=0.5)
    start_range = end_range - timedelta(days=30)
    fig.update_layout(xaxis=dict(range=[start_range, end_range]))

    st.plotly_chart(fig, use_container_width=True)


number_hours = 4

time_frame = "minute"
time_limit = datetime.utcnow() - timedelta(hours=number_hours)
result = hour_trans_by_account(time_limit=time_limit, time_frame=time_frame)
df_hour = pd.DataFrame(result)
st.title(f"Last {number_hours} hours of {metric_desc} per minute by Accounts")
if df_hour.empty:
    st.markdown("## No data")

else:
    df_hour.set_index("timestamp", inplace=True)
    df_hour["total_size_kb"] = df_hour["total_size"] / (1024 * 1)

    df_hour_no_account = pd.DataFrame(hour_trans_no_account(time_limit, time_frame))
    df_hour_no_account.set_index("timestamp", inplace=True)
    df_hour_no_account["total_size_kb"] = df_hour_no_account["total_size"] / (1024 * 1)

    all_accounts_desc_hour = df_hour.groupby('account')[metric].describe().sort_values(by='mean', ascending=False)
    all_accounts = all_accounts_desc_hour.index
    logging.info(f"Data loaded for fig 2: {timer() - start}")
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    df_hour['marker_size'] = np.log10(df_hour['total_size'])
    for account in all_accounts:
        fig2.add_trace(
            go.Scatter(
                x=df_hour[df_hour.account == account].index,
                y=df_hour[df_hour.account == account][metric],
                name=account,
                mode="markers",
                marker=dict(
                    size=10 + df_hour[df_hour.account == account]['marker_size']
                ),
                text=df_hour[df_hour.account == account]["account"],
                hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
            ),
            secondary_y=True,
        )
    fig2.add_trace(
        go.Scatter(
            x=df_hour_no_account.index,
            y=df_hour_no_account[metric],
            name=metric_desc,
            text=[f"{metric_desc}" for _ in df_no_account.index],
            hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=df_hour_no_account.index,
            y=df_hour_no_account[metric].rolling("1H").mean(),
            name=f"{metric_desc} (1hr Avg)",
            text=[f"{metric_desc} (1hr Avg)" for _ in df_no_account.index],
            hovertemplate="%{text}" + "<br>%{x}" + "<br>%{y:,.0f}",
        )
    )

    # fig2.update_layout(
    #     legend=dict(orientation="v", yanchor="top", y=0, xanchor="auto", x=1.15)
    # )
    fig2.update_layout(margin={"autoexpand": True, "b": 25, "t": 25, "l": 5, "r": 5})

    fig2.update_yaxes(title_text=metric_desc, secondary_y=False, showgrid=False)
    fig2.update_layout(title_x=0.05, title_y=0.9)

    fig2.update_yaxes(
        title_text=f"{metric_desc} by account", secondary_y=True, showgrid=False
    )
    fig2.update_layout(
        title_text=f"Last {number_hours} hours of {metric_desc} per minute by Accounts"
    )

    fig2.update_xaxes(showspikes=True)
    fig2.update_yaxes(showspikes=True)

    st.plotly_chart(fig2, use_container_width=True)

    cols = st.columns(2)
    cols[0].subheader(body=f"{metric_desc} Sent per Hour by each account")
    cols[0].dataframe(all_accounts_desc)
    cols[1].subheader(f"Last {number_hours} hours of {metric_desc} per minute by Accounts")
    cols[1].dataframe(all_accounts_desc_hour)
    logging.info(f"Everything done: {timer() - start}")