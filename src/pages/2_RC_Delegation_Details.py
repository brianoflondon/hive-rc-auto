# Contents of ~/my_app/pages/page_2.py
import logging

import streamlit as st
from hive_rc_auto.helpers.rc_delegation import RCDirectDelegation
from RC_Overview import get_data

st.markdown("# RC Delegation Details")
st.sidebar.markdown("# Details")

try:
    df = st.session_state.df_rc_changes
    df.sort_values(by='age', ascending=True, inplace=True)
    if not df.empty:
        df['link'] = f"[Link](https://hive.ausbit.dev/tx/" + df['trx_id'] + ")"
        df = df.drop(["deleg", "age", "trx_num", "trx_id", "block_num", "account"], axis=1)
        mkd = df.to_markdown()
        st.markdown(mkd)
        st.dataframe(df, use_container_width=True)


except AttributeError:
    pass
except Exception as e:
    logging.error(e)
