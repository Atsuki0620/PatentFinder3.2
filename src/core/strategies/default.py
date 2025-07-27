from typing import Tuple
from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter
import textwrap
from .base import BaseStrategy
from ..state import SearchConditions

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
            query_params.append(ArrayQueryParameter("countries", "STRING", conditions.countries))

        # --- 主語と述語を合わせたOR条件を構築 ---
        main_conditions = []
        all_keywords = list(set(conditions.subject_keywords + conditions.predicate_keywords))
        if all_keywords:
            kw_conds = []
            for kw in all_keywords:
                param_name = f"kw_{param_counter}"
                kw_conds.append(f"LOWER(p.search_text) LIKE @{param_name}")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
                param_counter += 1
            main_conditions.append(f"({' OR '.join(kw_conds)})")

        all_ipc = list(set(conditions.subject_ipc + conditions.predicate_ipc))
        if all_ipc:
            ipc_conds = []
            for code in all_ipc:
                param_name = f"ipc_{param_counter}"
                ipc_conds.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
                query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
                param_counter += 1
            main_conditions.append(f"({' OR '.join(ipc_conds)})")
        
        if main_conditions:
            where_clauses.append(f"({' OR '.join(main_conditions)})")

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
