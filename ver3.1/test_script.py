import openai
import os
import json
from google.cloud import bigquery
from google.api_core import exceptions

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
    print("エラー: OpenAI APIキーが設定されていません。")
    exit()

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Helper Functions ---

def call_openai_api(prompt):
    """OpenAI APIを呼び出し、JSONレスポンスを返す共通関数"""
    try:
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"OpenAI API呼び出し中にエラーが発生しました: {e}")
        return None

# --- Main Functions ---

def get_user_topic():
    """テスト用のトピックを返します。"""
    topic = "逆浸透膜における機械学習を用いた運転最適化"
    print("="*50)
    print("AI特許調査アシスタント (自動テスト版)")
    print("="*50)
    print(f"調査したい技術テーマ: {topic}")
    return topic

def generate_keywords(topic):
    """OpenAIを使用してキーワード候補を生成します。"""
    print("\n--- ステップ1: キーワードの拡張 ---")
    print("テーマを分析し、キーワードを提案します...")
    prompt = f"""
    あなたは熟練した特許調査の専門家です。技術テーマを核となる構成要素に分解し、各要素の同義語や関連語を提案してください。
    技術テーマ: "{topic}"
    JSON形式で、キー "components" に、"component_name" と "keywords" を持つオブジェクトのリストを返してください。
    例: {{\"components\": [{{\"component_name\": \"ドローン技術\", \"keywords\": [\"UAV\", \"無人航空機\"]}}]}}
    """
    response_json = call_openai_api(prompt)
    if response_json and 'components' in response_json:
        print("キーワード候補を生成しました。")
        return response_json['components']
    else:
        print("キーワード生成に失敗しました。")
        return None

def select_keywords(components):
    """テストのため、全てのキーワードを自動選択します。"""
    selected_keywords = {}
    if not components:
        return selected_keywords
    print("\n--- キーワード選択 (自動) ---")
    for component in components:
        name = component.get('component_name')
        keywords = component.get('keywords', [])
        if not name or not keywords:
            continue
        print(f"カテゴリ '{name}': 全て選択")
        selected_keywords[name] = keywords
    return selected_keywords

def generate_patent_classes(topic, selected_keywords):
    """関連する特許分類を推薦します。"""
    print("\n--- ステップ2: 特許分類の推薦 ---")
    print("キーワードを基に特許分類（CPC）を提案します...")
    all_keywords = [kw for sublist in selected_keywords.values() for kw in sublist]
    keywords_str = ", ".join(all_keywords)
    prompt = f"""
    あなたは熟練した特許調査の専門家です。技術テーマとキーワードに基づき、関連性の高い国際特許分類（CPC）を3〜5個推薦してください。
    技術テーマ: "{topic}"
    キーワード: "{keywords_str}"
    JSON形式で、キー "patent_classes" に、"class_code" と "description" を持つオブジェクトのリストを返してください。
    例: {{\"patent_classes\": [{{\"class_code\": \"B01D 61/02\", \"description\": \"逆浸透（RO）による分離プロセス\"}}]}}
    """
    response_json = call_openai_api(prompt)
    if response_json and 'patent_classes' in response_json:
        print("特許分類候補を生成しました。")
        return response_json['patent_classes']
    else:
        print("特許分類生成に失敗しました。")
        return None

def select_patent_classes(components):
    """テストのため、全ての分類を自動選択します。"""
    selected_classes = []
    if not components:
        return selected_classes
    print("\n--- 特許分類選択 (自動) ---")
    for component in components:
        class_code = component.get('class_code')
        if class_code:
            print(f"分類 '{class_code}': 選択")
            selected_classes.append(class_code)
    return selected_classes

def generate_sql_query(selected_keywords, selected_classes):
    """SQLクエリを生成します（高精度検索に固定）。"""
    print("\n--- ステップ3: SQLクエリの生成 ---")
    clauses = []
    for kws in selected_keywords.values():
        if kws:
            clauses.append(f"({' OR '.join([f'LOWER(abstract_localized.text) LIKE \'%{{kw.lower()}}%\'' for kw in kws])})")
    keyword_condition = " AND ".join(clauses)

    class_condition = ""
    if selected_classes:
        class_clauses = [f"code LIKE '{c}%'" for c in selected_classes]
        class_condition = f"publication_number IN (SELECT publication_number FROM `patents-public-data.us.cpc` WHERE {' OR '.join(class_clauses)})"

    where_parts = [part for part in [keyword_condition, class_condition] if part]
    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    final_sql = f"""
SELECT publication_number, title_localized.text AS title
FROM `patents-public-data.us.publications`,
UNNEST(title_localized) AS title_localized,
UNNEST(abstract_localized) AS abstract_localized
{where_clause}
LIMIT 10
"""
    print("\n--- 生成されたSQLクエリ ---")
    print(final_sql)
    return final_sql

def execute_bigquery_query(sql_query):
    """BigQueryでクエリを実行します。"""
    if not sql_query.strip() or "WHERE" not in sql_query:
        print("有効な検索条件がないため、BigQuery検索をスキップします。")
        return None
    print("\n--- ステップ4: BigQueryでの検索実行 ---")
    try:
        bq_client = bigquery.Client()
        query_job = bq_client.query(sql_query)
        results = list(query_job.result()) # 結果をリストに変換
        print(f"検索が完了しました。{len(results)}件の特許が見つかりました。")
        return results
    except Exception as e:
        print(f"BigQuery実行中にエラーが発生しました: {e}")
        return None

def main():
    topic = get_user_topic()
    keyword_components = generate_keywords(topic)
    if not keyword_components: return
    selected_keywords = select_keywords(keyword_components)
    
    patent_class_components = generate_patent_classes(topic, selected_keywords)
    selected_classes = []
    if patent_class_components:
        selected_classes = select_patent_classes(patent_class_components)

    sql_query = generate_sql_query(selected_keywords, selected_classes)
    results = execute_bigquery_query(sql_query)

    if results:
        print("\n--- 検索結果 ---")
        for i, row in enumerate(results, 1):
            print(f"[{i}] 特許番号: {row.publication_number}, タイトル: {row.title}")

if __name__ == "__main__":
    main()
