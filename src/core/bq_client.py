import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.bigquery import QueryJobConfig
from google.api_core import exceptions
import pandas as pd
from typing import Optional, Dict, Any

class BQClientError(Exception):
    """BigQueryクライアントで発生したエラーのためのカスタム例外"""
    pass

def execute_query(sql: str, params: list, credentials_info: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
    """
    GCP認証情報を使用し、クエリをBigQueryで実行する。
    テストとStreamlitアプリの両方から呼び出せるように、認証情報の注入を可能にする。
    成功した場合はDataFrameを、失敗した場合はNoneを返す。
    """
    try:
        creds_info_to_use = None
        if credentials_info:
            # テストスクリプトからの呼び出し
            creds_info_to_use = credentials_info
        elif st.session_state.get("gcp_sa_key_configured"):
            # Streamlitアプリからの呼び出し
            creds_info_to_use = st.session_state.get("gcp_sa_credentials")
        else:
            raise BQClientError("GCPの認証情報が設定されていません。")

        if not creds_info_to_use:
             raise BQClientError("認証情報が見つかりません。")

        credentials = service_account.Credentials.from_service_account_info(creds_info_to_use)
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        
        job_config = QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        results = query_job.result()
        return results.to_dataframe()

    except exceptions.BadRequest as e:
        error_details = "\n".join([err['message'] for err in e.errors])
        error_message = f"BigQueryのクエリエラーが発生しました。SQLの構文を確認してください。\n--- Details ---\n{error_details}"
        if credentials_info:
            raise BQClientError(error_message) from e
        else:
            st.error(error_message)
            return None
    except Exception as e:
        error_message = f"BigQueryの実行中に予期せぬエラーが発生しました: {e}"
        if credentials_info:
            raise BQClientError(error_message) from e
        else:
            st.error(error_message)
            return None

