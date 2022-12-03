import os
from datetime import datetime

import pandas as pd
import streamlit as st
from pymongo import MongoClient
from pymongo.command_cursor import CommandCursor

DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)
TIME_FRAME = "hour"


def all_trans_by_account(
    time_frame: str = TIME_FRAME, time_range: str = None, livetest_filter: str = None
) -> CommandCursor:
    if not time_range:
        time_range = st.session_state.time_range
    if not livetest_filter:
        livetest_filter = st.session_state.livetest_filter

    result = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            time_range,
            livetest_filter,
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


def all_trans_no_account(
    time_frame: str = TIME_FRAME, time_range: str = None, livetest_filter: str = None
) -> CommandCursor:
    if not time_range:
        time_range = st.session_state.time_range
    if not livetest_filter:
        livetest_filter = st.session_state.livetest_filter

    result_no_account = CLIENT["pingslurp"]["meta_ts"].aggregate(
        [
            time_range,
            livetest_filter,
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


def hour_trans_by_account(time_limit: datetime, time_frame: str) -> CommandCursor:
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


def hour_trans_no_account(time_limit: datetime, time_frame: str) -> CommandCursor:
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


def dataframe_all_transactions_by_account(
    time_frame: str = TIME_FRAME, time_range: str = None, livetest_filter: str = None
) -> pd.DataFrame:
    """
    Return DataFrame with all transactions divided up by time_frame
    """
    if not time_range:
        time_range = st.session_state.time_range
    if not livetest_filter:
        livetest_filter = st.session_state.livetest_filter

    result_all_trans = all_trans_by_account(
        time_frame=time_frame, time_range=time_range, livetest_filter=livetest_filter
    )
    df = pd.DataFrame(result_all_trans)
    if not df.empty:
        df.set_index("timestamp", inplace=True)
        df["total_size_kb"] = df["total_size"] / (1024 * 1)

    return df


def dataframe_all_transactions_no_account(
    time_frame: str = TIME_FRAME, time_range: str = None, livetest_filter: str = None
) -> pd.DataFrame:
    """
    Return DataFrame with all transactions divided up by time_frame
    Summary data for all accounts
    """
    if not time_range:
        time_range = st.session_state.time_range
    if not livetest_filter:
        livetest_filter = st.session_state.livetest_filter

    result_all_trans = all_trans_no_account(
        time_frame=time_frame, time_range=time_range, livetest_filter=livetest_filter
    )
    df = pd.DataFrame(result_all_trans)
    if not df.empty:
        df.set_index("timestamp", inplace=True)
        df["total_size_kb"] = df["total_size"] / (1024 * 1)

    return df
