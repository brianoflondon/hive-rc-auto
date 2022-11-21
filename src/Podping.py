
import streamlit as st
from hive_rc_auto.helpers.markdown.static_text import import_text
ALL_MARKDOWN = import_text()

st.title("Podping and Pingslurp")
st.sidebar.markdown("# Podping and Pingslurp")
st.markdown(ALL_MARKDOWN['home_page'], unsafe_allow_html=True)