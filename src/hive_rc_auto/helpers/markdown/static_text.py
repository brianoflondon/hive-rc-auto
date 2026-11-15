from glob import glob
from os.path import dirname, exists
from pathlib import Path

import streamlit as st

ALL_MARKDOWN = {}

HIVE_LINK = "[This project built on Hive](https://hive.io)"


def show_built_on_hive() -> None:
    """Credit link at the bottom of the sidebar on every Streamlit page."""
    st.sidebar.markdown(HIVE_LINK)


def import_text():
    files = glob(f"{dirname(__file__)}/*.md")
    for filepath in files:
        if exists(filepath):
            with open(filepath, "r") as f:
                file = Path(filepath).stem
                ALL_MARKDOWN[file] = f.read()
    return ALL_MARKDOWN
