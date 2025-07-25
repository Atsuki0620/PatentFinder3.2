from google.cloud import bigquery
from google.cloud.bigquery import Client, QueryJobConfig, ScalarQueryParameter
import pandas as pd
from core.state import SearchQuery
import streamlit as st
from typing import List, Tuple

def build_patent_query(query: SearchQuery) -> Tuple[str, List[ScalarQueryParameter]]:
    """
    検索条件オブジェクトからBigQueryのSQL文とクエリパラメータを構築する。
    UI表示とクエリ実行の両方で利用される共通ロジック。
    """
    query_params = []
    where_conditions = []

    # CTE to unnest localized fields first, avoiding alias reference issues in WHERE.
    # It prioritizes Japanese text but falls back to English.
    with_clause = """
WITH localized_patents AS (
  SELECT
    p.publication_number,
    (SELECT text FROM UNNEST(p.title_localized)    WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS title,
    (SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS abstract,
    (SELECT text FROM UNNEST(p.claims_localized)   WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS claims,
    (SELECT STRING_AGG(name) FROM UNNEST(p.assignee_harmonized)) as assignee_harmonized,
    p.publication_date,
    p.ipc
  FROM `patents-public-data.patents.publications` AS p
)
"""

    # --- Build WHERE clause ---
    # Date condition (required)
    # Use default values if the date strings are empty or None.
    pub_from_str = getattr(query, 'publication_date_from', None) or "20200101"
    pub_to_str = getattr(query, 'publication_date_to', None) or "20250714"

    where_conditions.append("publication_date BETWEEN @pub_from AND @pub_to")
    query_params.append(ScalarQueryParameter("pub_from", "INT64", int(pub_from_str.replace('-', ''))))
    query_params.append(ScalarQueryParameter("pub_to", "INT64", int(pub_to_str.replace('-', ''))))

    # IPC and Keyword conditions
    sub_where_parts = []
    
    # IPC conditions
    if hasattr(query, 'ipc_codes') and query.ipc_codes:
        ipc_wheres = []
        for i, code in enumerate(query.ipc_codes):
            param_name = f"ipc{i}"
            ipc_wheres.append(f"EXISTS (SELECT 1 FROM UNNEST(ipc) c WHERE c.code LIKE @{param_name})")
            query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
        if ipc_wheres:
            sub_where_parts.append(f"({' OR '.join(ipc_wheres)})")

    # Keyword conditions
    if hasattr(query, 'keywords') and query.keywords:
        keyword_wheres = []
        for i, kw in enumerate(query.keywords):
            param_name = f"kw{i}"
            # Each keyword is checked against all text fields, and these checks are ORed together.
            keyword_sub_wheres = [
                f"LOWER(title) LIKE @{param_name}",
                f"LOWER(abstract) LIKE @{param_name}",
                f"LOWER(claims) LIKE @{param_name}"
            ]
            keyword_wheres.append(f"({' OR '.join(keyword_sub_wheres)})")
            query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
        if keyword_wheres:
            # All individual keyword blocks are ORed together.
            sub_where_parts.append(f"({' OR '.join(keyword_wheres)})")

    # Combine IPC and Keyword clauses. A patent must match (the date range) AND ((any of the IPCs) OR (any of the keywords)).
    if sub_where_parts:
        where_conditions.append(f"({' OR '.join(sub_where_parts)})")

    # --- Assemble final SQL ---
    final_where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

    sql = f"""{with_clause}
SELECT
    publication_number,
    title,
    abstract,
    claims,
    assignee_harmonized,
    publication_date,
    (SELECT ARRAY_AGG(c.code) FROM UNNEST(ipc) AS c) AS ipc_codes
FROM localized_patents
WHERE {final_where_clause}
LIMIT @limit
"""
    query_params.append(ScalarQueryParameter("limit", "INT64", query.limit))

    return sql, query_params


@st.cache_data(show_spinner=False)
def search_patents_in_bigquery(_query: SearchQuery) -> pd.DataFrame:
    """
    build_patent_queryで生成したSQLを使い、BigQueryの公開特許データセットを検索する
    """
    print("--- Executing BigQuery Search ---")
    try:
        client = Client()
    except Exception as e:
        st.error(f"BigQueryクライアントの初期化に失敗しました。GCP認証情報を確認してください。: {e}")
        return pd.DataFrame()

    # SQLとパラメータを生成
    sql, query_params = build_patent_query(_query)

    job_config = QueryJobConfig(query_parameters=query_params)

    print("--- BigQuery実行クエリ ---")
    print(sql)
    print("--- クエリパラメータ ---")
    # Corrected the debug print statement from p.type to p.type_
    print([f"name: {p.name}, type: {p.type_}, value: {p.value}" for p in query_params])

    try:
        query_job = client.query(sql, job_config=job_config)
        results_df = query_job.result().to_dataframe()
        print(f"{len(results_df)}件の特許が見つかりました。")
        return results_df
    except Exception as e:
        st.error(f"BigQueryでの検索中にエラーが発生しました: {e}")
        # Return empty dataframe with expected columns on error
        expected_columns = [
            'publication_number', 'title', 'abstract', 'claims',
            'assignee_harmonized', 'publication_date', 'ipc_codes'
        ]
        return pd.DataFrame(columns=expected_columns)