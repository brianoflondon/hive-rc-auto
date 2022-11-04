from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from pymongo import MongoClient

# DB_CONNECTION="mongodb://100.68.99.92:27017/"
DB_CONNECTION = "mongodb://cepo-v4vapp:27017/"

client = MongoClient(DB_CONNECTION)

time_frame = "hour"
result = client["pingslurp"]["meta_ts"].aggregate(
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

df = pd.DataFrame(result)
df.set_index("timestamp", inplace=True)
all_accounts = df.account.unique()
fig = make_subplots(specs=[[{"secondary_y": True}]])
# fig.add_trace(
#     go.Scatter(x=df_no_account.index, y=df_no_account.total_iris, name="All Iris")
# )
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

fig.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="right", x=0.9)
)
fig.update_layout(title_x=0.2, title_y=0.2)
fig.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})
st.set_page_config(layout="wide")
st.plotly_chart(fig, use_container_width=True)



time_frame = 'minute'
time_limit =  datetime.utcnow() - timedelta(hours=1)
result = client['pingslurp']['meta_ts'].aggregate([
    {
        '$match':
            {
            'timestamp': {'$gt': time_limit},
            }
    },{
        '$group': {
            '_id': {
                'account': '$metadata.posting_auth',
                'timestamp': {
                    '$dateTrunc': {
                        'date': '$timestamp',
                        'unit': time_frame,
                        'timezone': 'Asia/Jerusalem'
                    }
                }
            },
            'timestamp' :{
                '$first': '$timestamp' },
            'account': {
                '$first': '$metadata.posting_auth'
            },
            'avg_size': {
                '$avg': '$json_size'
            },
            'total_size': {
                '$sum': '$json_size'
            },
            'total_podpings': {
                '$sum': 1
            },
            'total_iris': {
                '$sum': '$num_iris'
            }
        }
    }, {
        '$sort': {
            '_id.timestamp': -1
        }
    }
])

df_hour = pd.DataFrame(result)
df_hour.set_index("timestamp", inplace=True)
all_accounts = df_hour.account.unique()
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
for account in all_accounts:
    fig2.add_trace(
        go.Scatter(
            x=df_hour[df_hour.account == account].index,
            y=df_hour[df_hour.account == account].total_iris,
            name=account,
            mode="markers",
        ),
        secondary_y=True,
    )

fig2.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="right", x=0.9)
)
fig2.update_layout(title_x=0.2, title_y=0.2)
fig2.update_layout(margin={"autoexpand": True, "b": 0, "t": 0, "l": 0, "r": 0})

st.plotly_chart(fig2, use_container_width=True)
