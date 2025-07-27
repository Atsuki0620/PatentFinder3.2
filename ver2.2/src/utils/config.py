import os
import json
import tempfile
import streamlit as st
from dotenv import load_dotenv

def setup_api_keys(openai_api_key: str, gcp_sa_json_str: str):
    """
    UIから入力されたAPIキーとGCP認証情報を環境変数に設定する。
    GCP認証情報は一時ファイルに書き出し、そのパスを設定する。
    """
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
        st.success("OpenAI APIキーを設定しました。")
    else:
        st.warning("OpenAI APIキーが入力されていません。")

    if gcp_sa_json_str:
        try:
            # JSONとして有効か念のためパースしてみる
            json.loads(gcp_sa_json_str)
            
            # 一時ファイルにGCP認証情報を書き込む
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding='utf-8') as temp_file:
                temp_file.write(gcp_sa_json_str)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
            
            st.success("GCPサービスアカウント情報を設定しました。")
        except json.JSONDecodeError:
            st.error("GCPサービスアカウント情報のJSON形式が正しくありません。")
        except Exception as e:
            st.error(f"GCPサービスアカウント情報の設定中にエラーが発生しました: {e}")
    else:
        st.warning("GCPサービスアカウント情報が入力されていません。")

def load_env():
    """環境変数を.envファイルから読み込む"""
    load_dotenv()

def get_openai_api_key() -> str:
    """環境変数からOpenAI APIキーを取得する"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI APIキーが設定されていません。サイドバーから入力するか、.envファイルで設定してください。")
        st.stop()
    return api_key

def get_gcp_credentials_info() -> dict:
    """環境変数からGCP認証情報を取得し、内容を辞書として返す"""
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        st.error("GCPの認証情報(GOOGLE_APPLICATION_CREDENTIALS)が設定されていません。サイドバーから入力するか、.envファイルで設定してください。")
        st.stop()
    try:
        # If the credential is a JSON string
        if credentials_path.strip().startswith('{'):
            return json.loads(credentials_path)
        # If the credential is a file path
        else:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except FileNotFoundError:
        st.error(f"GCP認証ファイルが見つかりません: {credentials_path}")
        st.stop()
    except json.JSONDecodeError:
        st.error(f"GCP認証ファイルのJSON形式が正しくありません: {credentials_path}")
        st.stop()
    except Exception as e:
        st.error(f"GCP認証情報の読み込み中にエラーが発生しました: {e}")
        st.stop()
        return {} # st.stop() will exit, but return for completeness
