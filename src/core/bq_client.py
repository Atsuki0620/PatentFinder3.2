import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.bigquery import QueryJobConfig
from google.api_core import exceptions
import pandas as pd

def execute_query(sql: str, params: list) -> pd.DataFrame | None:
    """
    セッション状態のGCP認証情報を使用し、クエリをBigQueryで実行する。
    成功した場合はDataFrameを、失敗した場合はNoneを返す。
    """
    if not st.session_state.get("gcp_sa_key_configured"):
        st.error("GCPの認証情報が設定されていません。")
        return None

    try:
        credentials_info = st.session_state.get("gcp_sa_credentials")
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        
        job_config = QueryJobConfig(query_parameters=params)
        query_job = client.query(sql, job_config=job_config)
        results = query_job.result()
        return results.to_dataframe()

    except exceptions.BadRequest as e:
        error_details = "\n".join([err['message'] for err in e.errors])
        st.error(f"BigQueryのクエリエラーが発生しました。SQLの構文を確認してください。\n--- Details---\n{error_details}")
        return None
    except Exception as e:
        st.error(f"BigQueryの実行中に予期せぬエラーが発生しました: {e}")
        return None

