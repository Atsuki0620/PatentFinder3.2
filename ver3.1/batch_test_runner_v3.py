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

# --- Base Data ---
BASE_KEYWORDS = {
    "逆浸透膜技術": ["逆浸透膜", "RO膜", "海水淡水化"],
    "AI・機械学習": ["機械学習", "AI", "予測モデル", "最適化アルゴリズム"],
    "最適化・効率化": ["運転最適化", "効率化", "省エネルギー", "ファウリング"]
}
BASE_CLASSES = ["B01D61/02", "G05B13/02", "C02F1/44"]
RELAXED_CLASSES = ["B01D61/02", "G05B", "C02F1/44"] # G05B13/02 is relaxed to G05B

# --- Functions ---

def get_expanded_keywords():
    print("--- OpenAI APIを使い、キーワードを拡張しています... ---")
    prompt = f"""
    あなたは特許調査の専門家です。以下のキーワードグループについて、検索漏れを減らすために、それぞれ5つの技術的な同義語や関連語を追加してください。元のキーワードは必ず含めてください。
    元のキーワード: {json.dumps(BASE_KEYWORDS, ensure_ascii=False)}
    JSON形式で、元の構造を維持したまま返してください。
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        expanded = json.loads(response.choices[0].message.content)
        print("キーワードの拡張が完了しました。")
        # Ensure all original keywords are present
        for key, values in BASE_KEYWORDS.items():
            if key in expanded:
                expanded[key] = list(set(expanded[key] + values))
        return expanded
    except Exception as e:
        print(f"キーワード拡張中にエラーが発生しました: {e}")
        return BASE_KEYWORDS

def run_test(test_name, config):
    print(f"\n{'='*60}\n--- テスト開始: {test_name} ({config['description']}) ---\n{'='*60}")
    
    report_data = {
        "topic": "逆浸透膜における機械学習を用いた運転最適化",
        "sql": "", 
        "results": [], 
        "llm_evaluation": ""
    }
    
    key_path = os.path.join(os.path.dirname(__file__), 'corded-guild-459506-i6-5bc162f91e16.json')
    if not os.path.exists(key_path):
        print(f"エラー: サービスアカウントキーが見つかりません: {key_path}"); return
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    
    query_params = []
    param_counter = 0

    # Keyword Logic (OR across all keywords)
    all_kws = [kw for sublist in config["keywords"].values() for kw in sublist]
    keyword_or_conditions = []
    for kw in all_kws:
        param_name = f"keyword_{param_counter}"
        keyword_or_conditions.append(f"LOWER((SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1)) LIKE @{param_name}")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))
        param_counter += 1
    keyword_sql = f"({' OR '.join(keyword_or_conditions)})" if keyword_or_conditions else "1=0" # 1=0 to return false if no keywords

    # Class Logic (OR across all classes)
    cls_conditions = []
    for i, code in enumerate(config["classes"]):
        param_name = f"class_{i}"
        cls_conditions.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
    class_sql = f"({' OR '.join(cls_conditions)})" if cls_conditions else "1=0"

    where_clause = f"WHERE {class_sql} OR {keyword_sql}"

    sql = f"""
    SELECT p.publication_number,
           (SELECT text FROM UNNEST(p.title_localized) WHERE language IN ('en', 'ja') LIMIT 1) as title,
           (SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1) as abstract
    FROM `patents-public-data.patents.publications` AS p {where_clause} LIMIT 50
    """
    report_data["sql"] = sql
    
    try:
        bq_client = bigquery.Client()
        job_config = QueryJobConfig(query_parameters=query_params)
        results = list(bq_client.query(sql, job_config=job_config).result())
        for row in results:
            report_data["results"].append({"publication_number": row.publication_number, "title": row.title, "abstract": row.abstract})
        print(f"検索完了: {len(results)}件の特許を取得しました。")
    except Exception as e:
        print(f"BigQuery実行中にエラーが発生しました: {e}"); return

    # LLM Evaluation
    # ... (LLM evaluation logic remains the same)
    print("--- LLMによる検索結果の評価を実行中... ---")
    if not report_data["results"]:
        report_data["llm_evaluation"] = "検索結果は0件でした。"
    else:
        results_text = ""
        # Limit results sent to LLM to avoid being too verbose
        for i, res in enumerate(report_data['results'][:10], 1): # Send top 10 for evaluation
            results_text += f"[{i}] {res['publication_number']}\nタイトル: {res['title']}\n要約: {res['abstract']}\n\n"
        prompt = f"""
        # 指示
        あなたは特許調査の専門アナリストです。以下の調査テーマ、検索戦略、検索結果を分析し、調査の意図にマッチした特許を抽出できたかを評価してください。

        # 調査テーマ
        {report_data['topic']}

        # 検索戦略
        {config['description']}

        # 検索結果 (上位10件)
        {results_text}

        # 評価
        1. 各特許がテーマの要素（逆浸透膜、機械学習、最適化）をどの程度含んでいるか簡潔に分析してください。
        2. この検索戦略の有効性と結果の価値について考察してください。
        3. 最後に「結論：」として、調査の意図にマッチした特許を抽出できたか明確に判定してください。
        """
        try:
            response = client.chat.completions.create(model="gpt-4-turbo", messages=[{"role": "user", "content": prompt}])
            report_data["llm_evaluation"] = response.choices[0].message.content
            print("LLMによる評価が完了しました。")
        except Exception as e:
            report_data["llm_evaluation"] = f"LLM評価中にエラー: {e}"


    # Create Report
    print("--- レポートを作成中... ---")
    dir_name = f"inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_dir = os.path.join('investigations', dir_name)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f'summary_report_{test_name}.txt')
    
    report_content = f"""# 特許調査レポート ({test_name})

## 1. 調査テーマ
{report_data['topic']}

## 2. 検索戦略
{config['description']}

## 3. 実行されたSQLクエリ
```sql
{report_data['sql']}
```

## 4. 検索結果 ({len(report_data['results'])})件)
"""
    if not report_data['results']:
        report_content += "指定された条件に一致する特許は見つかりませんでした。\n"
    else:
        for i, res in enumerate(report_data['results'], 1):
            report_content += f"\n### [{i}] {res['publication_number']}\n- **タイトル:** {res['title']}\n- **要約:** {res['abstract']}\n---"
    
    report_content += f"\n\n## 5. LLMによる評価\n{report_data['llm_evaluation']}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\nレポートが正常に作成されました: {report_path}")

def main():
    expanded_keywords = get_expanded_keywords()

    TEST_CONFIGURATIONS = {
        "A_Keyword_Expansion": {
            "description": "IPCは元のまま、AIで拡張したキーワード群をOR条件で使用。キーワードの網羅性を高めて検索範囲を広げる。",
            "keywords": expanded_keywords,
            "classes": BASE_CLASSES
        },
        "B_IPC_Relaxation": {
            "description": "IPC分類を上位の階層に緩和し、キーワードは元のまま。OR条件で使用し、技術分野の裾野を広げる。",
            "keywords": BASE_KEYWORDS,
            "classes": RELAXED_CLASSES
        },
        "C_Both_Expanded_and_Relaxed": {
            "description": "キーワード拡張とIPC緩和を両方適用し、OR条件で使用。最も広範な関連技術を探索する。",
            "keywords": expanded_keywords,
            "classes": RELAXED_CLASSES
        }
    }

    for name, config in TEST_CONFIGURATIONS.items():
        run_test(name, config)
        time.sleep(2) # Ensure unique folder names

if __name__ == "__main__":
    main()
