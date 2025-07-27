import os
import json
import streamlit as st

def setup_api_keys(openai_api_key: str, gcp_sa_json_str: str):
    """
    UIから入力されたキーを検証し、セッション状態に保存する。
    """
    try:
        # OpenAI APIキーを設定
        st.session_state["openai_api_key"] = openai_api_key
        st.session_state.openai_api_key_configured = True

        # GCPサービスアカウントキーを検証・設定
        gcp_credentials = json.loads(gcp_sa_json_str)
        st.session_state["gcp_sa_credentials"] = gcp_credentials
        st.session_state.gcp_sa_key_configured = True
        
        st.success("APIキーが正常に設定されました。")
        return True
    except json.JSONDecodeError:
        st.error("GCPキーの形式が正しくありません。JSONファイルの中身を再度確認してください。")
        st.session_state.gcp_sa_key_configured = False
        return False
    except Exception as e:
        st.error(f"APIキーの設定中にエラーが発生しました: {e}")
        st.session_state.openai_api_key_configured = False
        st.session_state.gcp_sa_key_configured = False
        return False

def are_api_keys_configured():
    """
    両方のAPIキーが設定されているか確認する。
    """
    return st.session_state.get("openai_api_key_configured", False) and \
           st.session_state.get("gcp_sa_key_configured", False)
