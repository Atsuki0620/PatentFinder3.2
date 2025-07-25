import os
import json
from datetime import datetime
from google.cloud import bigquery
from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
import openai
import time

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
    print("エラー: OpenAI APIキーが設定されていません。")
    exit()
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Data for the Refined Strategy ---
REPORT_DATA = {
    "topic": "逆浸透膜における機械学習を用いた運転最適化",
    "strategy_description": "「技術の主語」を固定し、「述語」を緩和する戦略。特許分類において「逆浸透膜」関連(B01D61/02, C02F1/44)は必須とし、その上で、緩和した「制御システム」分類(G05B)に合致するか、または、いずれかのキーワードに合致する特許を検索する。",
    "subject_classes": ["B01D61/02", "C02F1/44"],
    "predicate_class_relaxed": "G05B",
    "keywords": {
        "逆浸透膜技術": ["逆浸透膜", "RO膜", "海水淡水化"],
        "AI・機械学習": ["機械学習", "AI", "予測モデル", "最適化アルゴリズム"],
        "最適化・効率化": ["運転最適化", "効率化", "省エネルギー", "ファウリング"]
    },
    "sql": "",
    "results": [],
    "llm_evaluation": ""
}

# --- Functions ---

def execute_bigquery_search():
    print("--- BigQueryでの検索を実行中 (主語固定・述語緩和 戦略)... ---")
    key_path = os.path.join(os.path.dirname(__file__), 'corded-guild-459506-i6-5bc162f91e16.json')
    if not os.path.exists(key_path):
        print(f"エラー: サービスアカウントキーが見つかりません: {key_path}"); return False
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    
    query_params = []
    param_counter = 0

    # --- Subject Classes (Must match one of these) ---
    subject_cls_conditions = []
    for i, code in enumerate(REPORT_DATA["subject_classes"]):
        param_name = f"s_class_{i}"
        subject_cls_conditions.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
    subject_sql = f"({" OR ".join(subject_cls_conditions)})";

    # --- Predicate Class (Relaxed) ---
    p_class_param = "p_class_0"
    predicate_cls_sql = f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{p_class_param})";
    query_params.append(ScalarQueryParameter(p_class_param, "STRING", f"{REPORT_DATA['predicate_class_relaxed']}%"))

    # --- Keywords (OR across all) ---
    all_kws = [kw for sublist in REPORT_DATA["keywords"].values() for kw in sublist]
    keyword_or_conditions = []
    for kw in all_kws:
        param_name = f"keyword_{param_counter}"
        keyword_or_conditions.append(f"LOWER((SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1)) LIKE @{param_name}")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
        param_counter += 1
    keyword_sql = f"({" OR ".join(keyword_or_conditions)})";

    # --- Final WHERE Clause ---
    where_clause = f"WHERE {subject_sql} AND ({predicate_cls_sql} OR {keyword_sql})";

    sql = f"""
    SELECT p.publication_number,
           (SELECT text FROM UNNEST(p.title_localized) WHERE language IN ('en', 'ja') LIMIT 1) as title,
           (SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1) as abstract
    FROM `patents-public-data.patents.publications` AS p {where_clause} LIMIT 50
    """
    REPORT_DATA["sql"] = sql;
    
    try:
        bq_client = bigquery.Client()
        job_config = QueryJobConfig(query_parameters=query_params)
        results = list(bq_client.query(sql, job_config=job_config).result())
        for row in results:
            REPORT_DATA["results"].append({"publication_number": row.publication_number, "title": row.title, "abstract": row.abstract})
        print(f"検索完了: {len(results)}件の特許を取得しました。")
        return True
    except Exception as e:
        print(f"BigQuery実行中にエラーが発生しました: {e}"); return False

def evaluate_results_with_llm():
    print("--- LLMによる検索結果の評価を実行中... ---")
    if not REPORT_DATA["results"]:
        REPORT_DATA["llm_evaluation"] = "検索結果は0件でした。主語となるIPC分類を持ち、かつ、述語となるIPC分類かキーワードのいずれかに合致する特許は見つかりませんでした。"
        return

    results_text = ""
    for i, res in enumerate(REPORT_DATA['results'][:15], 1): # Send top 15 for evaluation
        results_text += f"[{i}] {res['publication_number']}\nタイトル: {res['title']}\n要約: {res['abstract']}\n\n"
    prompt = f"""
    # 指示
    あなたは特許調査の専門アナリストです。以下の調査テーマ、検索戦略、検索結果を分析し、調査の意図にマッチした特許を抽出できたかを評価してください。

    # 調査テーマ
    {REPORT_DATA['topic']}

    # 検索戦略
    {REPORT_DATA['strategy_description']}

    # 検索結果 (上位15件)
    {results_text}

    # 評価
    1. 各特許が「主語（逆浸透膜）」と「述語（機械学習/最適化）」の要素をどの程度含んでいるか具体的に分析してください。
    2. この「主語固定」戦略が、以前の検索と比較してどの程度有効だったか考察してください。
    3. 最後に「結論：」として、調査の意図にマッチした特許を抽出できたか明確に判定してください。
    """
    try:
        response = client.chat.completions.create(model="gpt-4-turbo", messages=[{"role": "user", "content": prompt}])
        REPORT_DATA["llm_evaluation"] = response.choices[0].message.content
        print("LLMによる評価が完了しました。")
    except Exception as e:
        REPORT_DATA["llm_evaluation"] = f"LLM評価中にエラー: {e}"

def create_report():
    print("--- レポートを作成中... ---")
    dir_name = f"inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_dir = os.path.join('investigations', dir_name)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'summary_report_v5_refined.txt')
    
    report_content = f"""# 特許調査レポート (v5 - 主語固定・述語緩和 戦略)

## 1. 調査テーマ
{REPORT_DATA['topic']}

## 2. 検索戦略
{REPORT_DATA['strategy_description']}

## 3. 実行されたSQLクエリ
```sql
{REPORT_DATA['sql']}
```

## 4. 検索結果 ({len(REPORT_DATA['results'])}件)
"""
    if not REPORT_DATA['results']:
        report_content += "指定された条件に一致する特許は見つかりませんでした。\n"
    else:
        for i, res in enumerate(REPORT_DATA['results'], 1):
            report_content += f"\n### [{i}] {res['publication_number']}\n- **タイトル:** {res['title']}\n- **要約:** {res['abstract']}\n---"
    
    report_content += f"\n\n## 5. LLMによる評価\n{REPORT_DATA['llm_evaluation']}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\nレポートが正常に作成されました: {report_path}")

def main():
    if execute_bigquery_search():
        evaluate_results_with_llm()
    create_report()

if __name__ == "__main__":
    main()