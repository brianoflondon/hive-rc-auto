import os

import httpx
import pandas as pd
import streamlit as st
from pymongo import MongoClient

from hive_rc_auto.helpers.markdown.static_text import import_text

ALL_MARKDOWN = import_text()
DB_CONNECTION = os.getenv("DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)
from datetime import datetime, timedelta, timezone

st.set_page_config(
    page_title="Duplicated Feeds",
    page_icon="pages/android-chrome-512x512.png",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items=None,
)

time_range = st.sidebar.slider(
    "Time Range (hours) to examine:", min_value=-12, max_value=0, value=(-1, 0)
)
st.sidebar.write("Time Range", time_range)
(start_hours, end_hours) = time_range
num_hours = end_hours - start_hours


duplicate_count = st.sidebar.slider(
    label="Duplicate Threshold", min_value=3, max_value=18 + num_hours * 2, value=5
)


start_date = datetime.now(timezone.utc) + timedelta(hours=start_hours)
end_data = datetime.now(timezone.utc) + timedelta(hours=end_hours)

result = CLIENT["pingslurp"]["all_podpings"].aggregate(
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
            "$unwind": {
                "path": "$iris",
                "includeArrayIndex": "iri_pos",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {"$group": {"_id": "$iris", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": duplicate_count}}},
        {"$sort": {"count": -1}},
    ]
)
st.sidebar.markdown(ALL_MARKDOWN["duplicated_feeds"])
st.header(
    f"List of feeds with more than {duplicate_count} podpings in {num_hours} hours."
)


df = pd.DataFrame(result)
df.rename(columns={"_id": "iri"}, inplace=True)
print(df)
st.dataframe(df)

for index, row in df.iterrows():
    print(row["iri"], row["count"])
