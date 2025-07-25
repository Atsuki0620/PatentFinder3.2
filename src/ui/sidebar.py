import streamlit as st
from utils import config

def show():
    """サイドバーのUIを表示する"""
    with st.sidebar:
        st.title("PatentFinder 3.2")
        st.info("AIとの対話で特許調査を支援します。")

        st.header("APIキー設定")
        
        openai_configured = st.session_state.get("openai_api_key_configured", False)
        gcp_configured = st.session_state.get("gcp_sa_key_configured", False)

        if openai_configured and gcp_configured:
            st.success("両方のAPIキーが設定済みです。")
        else:
            st.warning("APIキーが未設定です。")

        with st.expander("APIキーを入力", expanded=not(openai_configured and gcp_configured)):
            openai_api_key = st.text_input(
                "OpenAI API Key", 
                type="password", 
                placeholder="sk-...",
                help="OpenAIのサイトで取得したAPIキーを入力してください。"
            )
            gcp_sa_json_str = st.text_area(
                "GCP Service Account JSON", 
                placeholder='''{
  "type": "service_account",
  ...
}''',
                height=300,
                help="GCPからダウンロードしたサービスアカウントキー(JSONファイル)の中身をそのまま貼り付けてください。"
            )

            if st.button("APIキーを設定"):
                if openai_api_key and gcp_sa_json_str:
                    if config.setup_api_keys(openai_api_key, gcp_sa_json_str):
                        st.rerun()
                else:
                    st.error("両方のキーを入力してください。")



