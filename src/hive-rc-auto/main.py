import numpy as np
import pandas as pd
import streamlit as st
import os

if __name__ == "__main__":
    st.set_page_config(
        page_title="Ex-stream-ly Cool App",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title('RC Monitor')
    #to get the current working directory
    directory = os.getcwd()

    print(directory)
    st.code(directory, language="log")
    with open("hive-rc-auto/data/example.log", "r") as f:
        st.code(f.read(), language="log")
