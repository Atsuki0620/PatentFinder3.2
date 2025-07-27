import openai
import os
import json
from google.cloud import bigquery
from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
    print("エラー: OpenAI APIキーが設定されていません。")
    exit()
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Helper Functions ---
def call_openai_api(prompt):
    try:
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model="gpt-4-turbo", messages=messages, response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"API Error: {e}")
        return None

# --- Main Functions ---
def get_user_topic():
    print("="*50)
    print("AI特許調査アシスタント (v2 - 実績コードベース)")
    print("="*50)
    return input("調査したい技術テーマを入力してください: ")

def generate_and_select_keywords(topic):
    print("\n--- ステップ1: キーワードの生成と選択 ---")
    prompt = f"""
    技術テーマ「{topic}」を構成要素に分解し、それぞれ5-7個の関連キーワードをJSONで提案してください。
    形式: {{\"components\": [{{\"component_name\": \"...\", \"keywords\": [...]}}]}}
    """
    response_json = call_openai_api(prompt)
    if not (response_json and 'components' in response_json):
        print("キーワード生成に失敗しました。")
        return {}

    selected_keywords = {}
    for component in response_json['components']:
        name = component.get('component_name')
        keywords = component.get('keywords', [])
        if not name or not keywords: continue

        print(f"\nカテゴリ: {name}")
        print("含めたいキーワードの番号をカンマ区切りで入力 (例: 1,3,5)。全ては'all', 不要はEnter:")
        for i, keyword in enumerate(keywords, 1): print(f"  {i}: {keyword}")
        
        user_input = input("> ").lower()
        if not user_input.strip(): continue
        if user_input == 'all':
            selected_keywords[name] = keywords
        else:
            try:
                indices = [int(i.strip()) - 1 for i in user_input.split(',')]
                selected_keywords[name] = [keywords[i] for i in indices if 0 <= i < len(keywords)]
            except ValueError:
                print("無効な入力です。")
    return selected_keywords

def generate_and_select_classes(topic, keywords):
    print("\n--- ステップ2: 特許分類の生成と選択 ---")
    all_kws = [kw for sublist in keywords.values() for kw in sublist]
    prompt = f"""
    技術テーマ「{topic}」とキーワード「{", ".join(all_kws)}」に基づき、関連性の高いCPC分類を3-5個JSONで提案してください。
    形式: {{\"patent_classes\": [{{\"class_code\": \"...\", \"description\": \"...\"}}]}}
    """
    response_json = call_openai_api(prompt)
    if not (response_json and 'patent_classes' in response_json):
        print("特許分類の生成に失敗しました。")
        return []

    selected_classes = []
    for pc in response_json['patent_classes']:
        code = pc.get('class_code')
        desc = pc.get('description', '')
        if not code: continue
        print(f"\n分類: {code} - {desc}")
        if input("この分類を含めますか？ (y/n): ").lower() == 'y':
            selected_classes.append(code)
    return selected_classes

def execute_bigquery_search(keywords, classes):
    print("\n--- ステップ3: BigQueryでの検索実行 ---")
    
    # 1. 認証情報の設定
    key_path = os.path.join(os.path.dirname(__file__), 'corded-guild-459506-i6-5bc162f91e16.json')
    if not os.path.exists(key_path):
        print(f"エラー: サービスアカウントキーが見つかりません: {key_path}")
        return
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    
    # 2. クエリとパラメータの動的構築
    all_kws = [kw for sublist in keywords.values() for kw in sublist]
    query_params = []
    
    # キーワード条件
    kw_conditions = []
    for i, kw in enumerate(all_kws):
        param_name = f"keyword_{i}"
        kw_conditions.append(f"LOWER((SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1)) LIKE @{param_name}")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"%{kw.lower()}%"))

    # 分類条件
    cls_conditions = []
    for i, code in enumerate(classes):
        param_name = f"class_{i}"
        cls_conditions.append(f"EXISTS (SELECT 1 FROM UNNEST(p.ipc) AS ipc WHERE ipc.code LIKE @{param_name})")
        query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))

    # Build WHERE clause with AND logic
    where_clause = ""
    kw_or_conditions = f"({' OR '.join(kw_conditions)})" if kw_conditions else ""
    cls_or_conditions = f"({' OR '.join(cls_conditions)})" if cls_conditions else ""

    if kw_or_conditions and cls_or_conditions:
        where_clause = f"WHERE {cls_or_conditions} AND {kw_or_conditions}"
    elif kw_or_conditions:
        where_clause = f"WHERE {kw_or_conditions}"
    elif cls_or_conditions:
        where_clause = f"WHERE {cls_or_conditions}"
    else:
        print("検索条件が指定されていません。")
        return

    # 3. SQL本体
    sql = f"""
    SELECT
        p.publication_number,
        (SELECT text FROM UNNEST(p.title_localized) WHERE language IN ('en', 'ja') LIMIT 1) as title,
        (SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('en', 'ja') LIMIT 1) as abstract
    FROM
        `patents-public-data.patents.publications` AS p
    {where_clause}
    LIMIT 20
    """
    
    print("\n--- 実行クエリ ---")
    print(sql)
    
    # 4. BigQueryクライアントの初期化と実行
    try:
        client = bigquery.Client()
        job_config = QueryJobConfig(query_parameters=query_params)
        query_job = client.query(sql, job_config=job_config)
        results = list(query_job.result())
        
        print(f"\n--- 検索結果: {len(results)}件 ---")
        for i, row in enumerate(results, 1):
            print(f"\n[{i}] 特許番号: {row.publication_number}")
            print(f"  タイトル: {row.title}")
            print(f"  要約: {row.abstract[:200] if row.abstract else ''}...")
            
    except Exception as e:
        print(f"BigQuery実行中にエラーが発生しました: {e}")

def main():
    topic = get_user_topic()
    selected_keywords = generate_and_select_keywords(topic)
    selected_classes = generate_and_select_classes(topic, selected_keywords)
    
    if not selected_keywords and not selected_classes:
        print("検索条件が何も選択されなかったため、処理を終了します。")
        return
        
    execute_bigquery_search(selected_keywords, selected_classes)

if __name__ == "__main__":
    main()