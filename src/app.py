import streamlit as st
from core.state import AppState
from ui import sidebar, main_view

# --- ページ設定 ---
st.set_page_config(
    page_title="PatentFinder 3.2",
    layout="wide"
)

# --- 状態管理 ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = AppState()
app_state: AppState = st.session_state.app_state

# --- UI描画 ---
sidebar.show()
main_view.show(app_state)

