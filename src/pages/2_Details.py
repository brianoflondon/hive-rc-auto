# Contents of ~/my_app/pages/page_2.py
import logging

import streamlit as st
from hive_rc_auto.helpers.rc_delegation import RCDirectDelegation
from RC_Overview import get_data

st.markdown("# Details ❄️")
st.sidebar.markdown("# Details ❄️")

try:
    df = st.session_state.df_rc_changes
    if not df.empty:
        df = df.drop(["deleg", "age", "trx_num", "trx_id", "block_num"], axis=1)
        st.dataframe(df)


except AttributeError:
    pass
except Exception as e:
    logging.error(e)
