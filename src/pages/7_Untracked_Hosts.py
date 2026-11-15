import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from pymongo import MongoClient

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.markdown.static_text import import_text, show_built_on_hive

ALL_MARKDOWN = import_text()
CLIENT = MongoClient(Config.PINGSLURP_DB_CONNECTION)
KNOWN_HOSTS_PATH = (
    Path(__file__).resolve().parents[1] / "hive_rc_auto" / "helpers" / "known_hosts.json"
)


def naive_utcnow() -> datetime:
    """Naive UTC, matching PyMongo's default tz_aware=False datetimes."""
    return datetime.now(UTC).replace(tzinfo=None)


def load_known_host_patterns() -> list[re.Pattern[str]]:
    patterns = json.loads(KNOWN_HOSTS_PATH.read_text())
    return [re.compile(pattern) for pattern in patterns.values()]


def is_tracked(url: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.match(url) for pattern in patterns)


def untracked_hosts(hours: int, min_pings: int) -> pd.DataFrame:
    """Hostnames in recent podping IRIs that match no known-host pattern."""
    start = naive_utcnow() - timedelta(hours=hours)
    patterns = load_known_host_patterns()
    rows = CLIENT["pingslurp"]["all_podpings"].aggregate([
        {"$match": {"timestamp": {"$gte": start}}},
        {"$unwind": "$iris"},
        {"$project": {"_id": 0, "iri": "$iris"}},
    ])
    counts: dict[str, int] = {}
    samples: dict[str, str] = {}
    for row in rows:
        iri = row.get("iri")
        if not isinstance(iri, str) or is_tracked(iri, patterns):
            continue
        host = urlparse(iri).hostname
        if not host:
            continue
        host = host.lower()
        counts[host] = counts.get(host, 0) + 1
        samples.setdefault(host, iri)
    table = [
        {"Pings": count, "Host": host, "Example": samples[host]}
        for host, count in counts.items()
        if count >= min_pings
    ]
    table.sort(key=lambda item: item["Pings"], reverse=True)
    return pd.DataFrame(table, columns=["Pings", "Host", "Example"])


st.set_page_config(
    page_title="Untracked Hosts",
    page_icon="pages/android-chrome-512x512.png",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items=None,
)

hours = st.sidebar.slider("Hours to look back", min_value=1, max_value=168, value=24)
min_pings = st.sidebar.slider("Minimum pings", min_value=1, max_value=100, value=10)
st.sidebar.markdown(ALL_MARKDOWN["untracked_hosts"])
show_built_on_hive()

st.header(f"Untracked hosts in the last {hours} hours")
with st.spinner("Reading podping URLs"):
    df = untracked_hosts(hours, min_pings)

if df.empty:
    st.info("No untracked hosts in this window at that minimum.")
else:
    st.dataframe(
        df,
        column_config={
            "Pings": st.column_config.NumberColumn("Pings", format="%d"),
            "Host": st.column_config.TextColumn("Host"),
            "Example": st.column_config.LinkColumn("Example"),
        },
        hide_index=True,
        width="stretch",
    )
