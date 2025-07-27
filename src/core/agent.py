import openai
from openai import OpenAI
import streamlit as st
import json
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .state import AppState
from .strategies.default import SubjectPredicateStrategy
from . import bq_client, reporter

# --- Prompt Templates ---

REFINE_THEME_PROMPT = """
あなたは特許調査の専門家です。ユーザーが入力した広範な調査テーマを分析し、より具体的で調査可能な技術テーマを3〜5個提案してください。
各テーマは「〇〇の技術」という形式で、簡潔に記述してください。

ユーザーの調査テーマ:
{user_query}

JSON形式で以下の構造で返してください:
{{
  "proposed_plans": [
    "（具体的なテーマ1）の技術",
    "（具体的なテーマ2）の技術",
    "（具体的なテーマ3）の技術"
  ]
}}
"""

SUGGEST_TERMS_PROMPT = """
あなたは特許調査の専門家です。以下の具体的な調査テーマに基づき、検索に有効なキーワードとIPC分類を提案してください。
テーマの核心（主語）と、その操作や目的（述語）を意識して、それぞれについて最も関連性の高いものを**3つ**ずつ提案してください。

調査テーマ:
{plan_text}

JSON形式で以下の構造で返してください:
{{
  "subject_keywords": ["...", "...", "..."],
  "subject_ipc": ["...", "...", "..."],
  "predicate_keywords": ["...", "...", "..."],
  "predicate_ipc": ["...", "...", "..."]
}}
"""

TRANSLATE_KEYWORDS_PROMPT = """
あなたは多言語対応の特許検索アシスタントです。
以下の日本語キーワードリストを、特許検索で一般的に使われる対応する英語キーワードに翻訳してください。
各日本語キーワードに対して、最も適切と思われる英語キーワードを3つまで提案してください。

日本語キーワード:
{keywords_jp}

JSON形式で、元の日本語をキー、英語リストをバリューとする辞書で返してください:
{{
  "翻訳結果": {{
    "日本語キーワード1": ["english_keyword1_1", "english_keyword1_2"],
    "日本語キーワード2": ["english_keyword2_1"]
  }}
}}
"""

def get_llm_response(prompt: str, json_mode: bool = False) -> str:
    """LLMからの応答を生成する共通関数"""
    if not st.session_state.get("openai_api_key_configured"):
        return json.dumps({"error": "OpenAI APIキーが設定されていません。"})
    try:
        client = OpenAI(api_key=st.session_state.get("openai_api_key"))
        messages = [{"role": "user", "content": prompt}]
        
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            response_format=response_format
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": f"LLMエラー: {e}"})

def run_initial_interaction(app_state: AppState) -> AppState:
    """ユーザーの最初の入力から、具体的な調査テーマの候補を複数生成する"""
    user_query = app_state.chat_history[-1][1]
    
    with st.spinner("調査テーマの具体的な選択肢を生成中..."):
        prompt = REFINE_THEME_PROMPT.format(user_query=user_query)
        response_str = get_llm_response(prompt, json_mode=True)
        
        try:
            response_data = json.loads(response_str)
            if "error" in response_data:
                raise Exception(response_data["error"])
            
            app_state.proposed_plans = response_data.get("proposed_plans", [])
            
            ai_response = "ご依頼内容について、より調査を具体的にするために、いくつかテーマの候補を提案します。中央カラムから最も関心に近いものを選択してください。"
            app_state.chat_history.append(("assistant", ai_response))

        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_msg = f"テーマ候補の生成に失敗しました。エラー: {e}"
            app_state.chat_history.append(("assistant", error_msg))
            app_state.error_message = error_msg

    return app_state

def suggest_search_terms(app_state: AppState) -> AppState:
    """確定したテーマに基づき、検索タームを提案する"""
    with st.spinner("具体的な検索キーワードとIPC分類を提案中..."):
        prompt = SUGGEST_TERMS_PROMPT.format(plan_text=app_state.plan_text)
        response_str = get_llm_response(prompt, json_mode=True)
        
        try:
            response_data = json.loads(response_str)
            if "error" in response_data:
                raise Exception(response_data["error"])

            app_state.search_conditions.subject_keywords = response_data.get("subject_keywords", [])
            app_state.search_conditions.subject_ipc = response_data.get("subject_ipc", [])
            app_state.search_conditions.predicate_keywords = response_data.get("predicate_keywords", [])
            app_state.search_conditions.predicate_ipc = response_data.get("predicate_ipc", [])
            app_state.terms_suggested = True

            ai_response = "調査テーマに基づき、具体的な検索条件を提案しました。中央カラムの「検索条件」タブで内容を確認・編集してください。"
            app_state.chat_history.append(("assistant", ai_response))

        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_msg = f"検索タームの提案に失敗しました。エラー: {e}"
            app_state.chat_history.append(("assistant", error_msg))
            app_state.error_message = error_msg
            
    return app_state

def get_embeddings(texts: list, model="text-embedding-3-small") -> list:
    client = OpenAI(api_key=st.session_state.get("openai_api_key"))
    response = client.embeddings.create(input=texts, model=model)
    return [embedding.embedding for embedding in response.data]

def run_search_callback():
    """
    Streamlitのボタンのon_clickコールバック用のラッパー関数。
    st.session_stateからapp_stateを取得してrun_searchを呼び出す。
    """
    app_state = st.session_state.app_state
    st.session_state.app_state = run_search(app_state)

def run_report_generation_callback():
    """
    Streamlitのボタンのon_clickコールバック用のラッパー関数。
    """
    app_state = st.session_state.app_state
    
    # main_viewで選択された特許番号リストを取得
    selected_numbers = st.session_state.get("selected_patent_numbers_for_report", [])
    
    if not selected_numbers:
        st.warning("レポートを生成するには、検索結果のテーブルで少なくとも1つの特許を選択してください。")
        return

    selected_rows = app_state.search_results[app_state.search_results["publication_number"].isin(selected_numbers)]
    
    with st.spinner("AIがレポートを生成中..."):
        report_md = reporter.generate_summary_report(app_state.plan_text, selected_rows)
        app_state.report_text = report_md
        ai_response = "レポートを生成しました。右カラムの「レポート」タブで確認してください。"
        app_state.chat_history.append(("assistant", ai_response))
    
    st.session_state.app_state = app_state

def run_search(app_state: AppState) -> AppState:
    """検索を実行し、結果を状態に保存する"""
    app_state.error_message = "" # 実行前にエラーメッセージをクリア
    with st.status("特許検索を実行中...", expanded=True) as status:
        try:
            # 0. 事前検証
            status.update(label="検索条件を検証中...")
            cond = app_state.search_conditions
            if not (cond.subject_keywords or cond.subject_ipc or cond.predicate_keywords or cond.predicate_ipc):
                app_state.error_message = "キーワードまたはIPCを少なくとも1つは指定してください。"
                status.update(label="検索条件がありません。", state="error")
                return app_state

            # 1. キーワード翻訳 (一時的に無効化)
            # status.update(label="日本語キーワードを英語に翻訳中...")
            # (翻訳ロジックはここにありますが、今回は呼び出しません)

            # 2. SQL生成
            status.update(label="SQLクエリを生成中...")
            strategy = SubjectPredicateStrategy()
            sql, params = strategy.generate_sql(app_state.search_conditions)
            app_state.generated_sql = sql
            
            # 3. BigQuery検索
            status.update(label=f"BigQueryで最大{app_state.search_conditions.limit}件の特許を検索中...")
            results_df = bq_client.execute_query(sql, params)
            
            if results_df is None:
                app_state.error_message = "BigQueryでの検索に失敗しました。UIに表示された詳細なエラーメッセージを確認してください。"
                status.update(label="BigQuery検索エラー", state="error")
                return app_state

            if results_df.empty:
                status.update(label="検索結果が0件でした。", state="complete")
                app_state.search_results = pd.DataFrame()
                ai_response = "検索条件に一致する特許は見つかりませんでした。"
                app_state.chat_history.append(("assistant", ai_response))
                return app_state
            
            # 4. 類似度計算
            status.update(label=f"{len(results_df)}件の文献の類似度を計算中...")
            plan_embedding = get_embeddings([app_state.plan_text])[0]
            
            results_df['text_for_embedding'] = results_df['title'].fillna('') + ' ' + results_df['abstract'].fillna('')
            document_embeddings = get_embeddings(results_df['text_for_embedding'].tolist())
            
            similarities = cosine_similarity([plan_embedding], document_embeddings)[0]
            results_df['similarity'] = similarities
            
            # 5. 結果のソートと保存
            results_df = results_df.sort_values(by='similarity', ascending=False).drop(columns=['text_for_embedding'])
            app_state.search_results = results_df
            
            status.update(label="検索完了！", state="complete")
            ai_response = f"検索が完了し、調査方針との類似度が高い順に{len(results_df)}件の特許をランキングしました。"
            app_state.chat_history.append(("assistant", ai_response))
        
        except Exception as e:
            app_state.error_message = f"検索処理中に予期せぬエラーが発生しました: {e}"
            st.error(app_state.error_message)
            status.update(label="エラーが発生しました", state="error")

    return app_state




