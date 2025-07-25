from typing import Tuple
from google.cloud.bigquery import ScalarQueryParameter
import textwrap
from .base import BaseStrategy
from core.state import SearchConditions

class SubjectPredicateStrategy(BaseStrategy):
    """
    「主語固定・述語緩和」戦略に、高度な検索条件を追加した戦略。
    CTEとシンプルなWHERE句を用いることで、堅牢性と可読性を高めた。
    """
    def generate_sql(self, conditions: SearchConditions) -> Tuple[str, list]:
        query_params = []
        param_counter = 0
        where_clauses = []

        # --- 共通条件 ---
        if conditions.start_date and conditions.end_date:
            where_clauses.append("p.publication_date BETWEEN @start_date AND @end_date")
            query_params.extend([
                ScalarQueryParameter("start_date", "INT64", int(conditions.start_date.strftime("%Y%m%d"))),
                ScalarQueryParameter("end_date", "INT64", int(conditions.end_date.strftime("%Y%m%d")))
            ])
        if conditions.countries:
            where_clauses.append("SUBSTR(p.publication_number, 1, 2) IN UNNEST(@countries)")
            query_params.append(ScalarQueryParameter("countries", "STRING", conditions.countries))

        # --- 主語 (ANDで結合) ---
        subject_parts = []
        if conditions.subject_keywords:
            kw_conds = []
            for kw in set(conditions.subject_keywords): # 重複除去
                param_name = f"s_kw_{param_counter}"
                kw_conds.append(f"LOWER(p.search_text) LIKE @{param_name}")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
                param_counter += 1
            subject_parts.append(f"({' OR '.join(kw_conds)})")
        
        if conditions.subject_ipc:
            ipc_conds = []
            for code in set(conditions.subject_ipc):
                param_name = f"s_ipc_{param_counter}"
                ipc_conds.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
                param_counter += 1
            subject_parts.append(f"({' OR '.join(ipc_conds)})")
        
        if subject_parts:
            where_clauses.append(f"({' AND '.join(subject_parts)})")

        # --- 述語 (ORで結合) ---
        predicate_parts = []
        if conditions.predicate_keywords:
            kw_conds = []
            for kw in set(conditions.predicate_keywords):
                param_name = f"p_kw_{param_counter}"
                kw_conds.append(f"LOWER(p.search_text) LIKE @{param_name}")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
                param_counter += 1
            predicate_parts.append(f"({' OR '.join(kw_conds)})")

        if conditions.predicate_ipc:
            ipc_conds = []
            for code in set(conditions.predicate_ipc):
                param_name = f"p_ipc_{param_counter}"
                ipc_conds.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
                param_counter += 1
            predicate_parts.append(f"({' OR '.join(ipc_conds)})")
            
        if predicate_parts:
            where_clauses.append(f"({' OR '.join(predicate_parts)})")

        where_sql = "WHERE\n  " + "\n  AND ".join(where_clauses) if where_clauses else ""

        sql = f"""
        WITH PatentData AS (
            SELECT
                publication_number,
                (SELECT text FROM UNNEST(title_localized) WHERE language IN ('en', 'ja') LIMIT 1) as title,
                (SELECT text FROM UNNEST(abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1) as abstract,
                (SELECT STRING_AGG(name) FROM UNNEST(assignee_harmonized)) as assignee,
                publication_date,
                ipc, -- IPCをそのまま渡す
                (SELECT STRING_AGG(code) FROM UNNEST(ipc)) as ipc_codes,
                CONCAT(
                    (SELECT text FROM UNNEST(title_localized) WHERE language IN ('en', 'ja') LIMIT 1), ' ',
                    (SELECT text FROM UNNEST(abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1)
                ) as search_text
            FROM
                `patents-public-data.patents.publications`
        )
        SELECT
            p.publication_number,
            p.title,
            p.abstract,
            p.assignee,
            p.publication_date,
            p.ipc_codes
        FROM
            PatentData p
        {where_sql}
        LIMIT @limit
        """
        query_params.append(ScalarQueryParameter("limit", "INT64", conditions.limit))
        
        return textwrap.dedent(sql.strip()), query_params
