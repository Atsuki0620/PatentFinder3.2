from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.bigquery import QueryJobConfig
from google.api_core import exceptions
import pandas as pd

class BQClientError(Exception):
    """BigQueryクライアントで発生したエラーのためのカスタム例外"""
    pass

def execute_query(sql: str, params: list, credentials_info: dict = None) -> pd.DataFrame:
    """
    クエリをBigQueryで実行する。
    成功した場合はDataFrameを、失敗した場合はBQClientErrorをraiseする。
    
    Args:
        sql (str): 実行するSQLクエリ。
        params (list): SQLクエリのパラメータ。
        credentials_info (dict, optional): GCPサービスアカウントの認証情報。
                                            Noneの場合、Streamlitのセッション状態から取得を試みる。

    Returns:
        pd.DataFrame: クエリの実行結果。

    Raises:
        BQClientError: 認証情報の不足、クエリエラー、その他の実行時エラーが発生した場合。
    """
    # 認証情報が引数で渡されなかった場合、Streamlitのセッション状態から取得を試みる
    if credentials_info is None:
        try:
            import streamlit as st
            if not st.session_state.get("gcp_sa_key_configured"):
                raise BQClientError("GCPの認証情報が設定されていません。")
            credentials_info = st.session_state.get("gcp_sa_credentials")
        except ImportError:
            raise BQClientError("Streamlit環境外で実行する場合、credentials_info引数に認証情報を渡す必要があります。")

    try:
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        
        job_config = QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        results = query_job.result()
        return results.to_dataframe()

    except exceptions.BadRequest as e:
        error_details = "\n".join([err['message'] for err in e.errors])
        raise BQClientError(f"BigQueryのクエリエラーが発生しました。SQLの構文を確認してください。\n--- Details---\n{error_details}") from e
    except Exception as e:
        raise BQClientError(f"BigQueryの実行中に予期せぬエラーが発生しました: {e}") from e

