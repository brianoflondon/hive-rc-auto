import asyncio
import os
from datetime import datetime, timedelta, timezone
from timeit import default_timer as timer
from typing import OrderedDict, Tuple

import httpx
import pandas as pd
import streamlit as st
import xmltodict
from pymongo import MongoClient

from hive_rc_auto.helpers.markdown.static_text import import_text
from hive_rc_auto.helpers.podcastindex import get_podcast_index_info

ALL_MARKDOWN = import_text()
DB_CONNECTION = os.getenv("PINGSLURP_DB_CONNECTION")
CLIENT = MongoClient(DB_CONNECTION)

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
df.set_index("count", inplace=True)
print(df)
st.dataframe(df)

iris = [row["iri"] for index, row in df.iterrows()]
iris = iris[:5]


async def lookup_all(df: pd.DataFrame):
    iris = [row["iri"] for index, row in df.iterrows()]
    ncol = 5
    iris = iris[: ncol * 2]
    answer = {}
    periods = {}
    async with asyncio.TaskGroup() as tg:
        for iri in iris:
            answer[iri] = tg.create_task(lookup_iri(iri))
            periods[iri] = tg.create_task(check_show_period(iri))

    cols = st.columns(ncol)
    n = 0
    for index, row in df.iterrows():
        iri = row["iri"]
        if answer.get(iri) and answer[iri].result():
            col = cols[n % ncol]
            (title, image) = answer[iri].result()
            (min_time, max_time, mean_time) = (
                periods[iri].result()["min"].total_seconds(),
                periods[iri].result()["max"].total_seconds(),
                periods[iri].result()["mean"].total_seconds(),
            )
            if image is None:
                image = "pages/android-chrome-512x512.png"
            col.image(image=image, width=100)
            col.write(title)
            col.write(f"Repeats: {index}")
            col.write("Seconds between pings:")
            col.write(f"min (s): {min_time:.0f}")
            col.write(f"max (s): {max_time:.0f}")
            col.write(f"mean(s): {mean_time:.0f}")
            col.write(iri)
            n += 1


def get_feed_title(feed_xml: OrderedDict) -> str | None:
    try:
        return feed_xml["rss"]["channel"]["title"]
    except Exception:
        return None


def get_feed_image(feed_xml: OrderedDict) -> str | None:
    try:
        return feed_xml["rss"]["channel"]["image"]["url"]
    except Exception:
        try:
            return feed_xml["rss"]["channel"]["itunes:image"]["@href"]
        except Exception:
            return None


async def lookup_iri(iri: str) -> Tuple[str, str]:
    async with httpx.AsyncClient() as client:
        user_agent = {"User-agent": "Pingslurp for Podping"}
        try:
            pod_info = await get_podcast_index_info(iri)
            if pod_info:
                if pod_info.artwork:
                    return pod_info.podcast, pod_info.artwork
                elif pod_info.image:
                    return pod_info.podcast, pod_info.image

            # Fetch RSS
            resp = await client.get(iri, headers=user_agent, follow_redirects=True)
            if resp.status_code == 200:
                feed_xml = xmltodict.parse(resp.content)
                title = get_feed_title(feed_xml)
                channel_image = get_feed_image(feed_xml)
                return title, channel_image
        except Exception as ex:
            print(iri, ex.__repr__(), ex)
            return iri, None


async def check_show_period(check_show: str) -> pd.DataFrame:
    print(f"Checking: {check_show}")
    start = timer()
    filter = {
        "iris": check_show,
        "$and": [
            {"timestamp": {"$gt": start_date}},
            {"timestamp": {"$lt": end_data}},
        ],
    }
    sort = list({"timestamp": -1}.items())
    one_show = CLIENT["pingslurp"]["all_podpings"].find(filter=filter, sort=sort)
    df_one_show = pd.DataFrame(one_show)
    periodicity = df_one_show.timestamp.diff(periods=-1).agg(
        func=["min", "max", "mean", "median", "std"]
    )
    print(f"Period check: {check_show} - {timer() - start:.2f} seconds")
    return periodicity


asyncio.run(lookup_all(df))
