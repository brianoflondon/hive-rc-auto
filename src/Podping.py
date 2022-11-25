
import streamlit as st
from hive_rc_auto.helpers.markdown.static_text import import_text
ALL_MARKDOWN = import_text()

st.set_page_config(page_title="Podping stats from Pingslurp", page_icon="src/pages/android-chrome-512x512.png", layout="wide", initial_sidebar_state="auto", menu_items=None)
st.title("Podping and Pingslurp")
st.sidebar.markdown("# Podping and Pingslurp")
st.markdown(ALL_MARKDOWN['home_page'], unsafe_allow_html=True)