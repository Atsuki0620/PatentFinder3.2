from langgraph.graph import StateGraph, END
from typing import Literal
from core.state import AppState, SearchQuery
from core.tools import build_patent_query, search_patents_in_bigquery
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
import os
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- モデル定義 ---
model = ChatOpenAI(temperature=0, model="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY"))
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.environ.get("OPENAI_API_KEY"))

# --- プロンプトテンプレート ---
# ルーター用プロンプト
ROUTER_PROMPT = ChatPromptTemplate.from_template(
    """あなたは、ユーザーとの対話の文脈と現在のアプリケーションの状態を読み解き、次に取るべきアクションを判断するルーターです。
    以下の情報から、ユーザーの意図を判断し、'continue_dialogue'（対話継続）、'generate_plan'（調査方針の生成）、'generate_query'（検索条件の生成）のいずれかを選択してください。

    対話履歴:
    {chat_history}

    現在の調査方針:
    {plan_text}

    判断基準:
    - ユーザーが最初の質問をしたばかり、または情報が不足している場合は 'continue_dialogue'。
    - 対話が進み、調査の方向性が見えてきたが、まだ具体的な調査方針が固まっていない場合は 'generate_plan'。
    - 調査方針が既に存在し、ユーザーが検索実行を指示した場合（例：「検索して」「これでOK」）、または調査方針が明確な場合は 'generate_query'。

    あなたの判断（'continue_dialogue', 'generate_plan', 'generate_query' のみを出力）:"""
)

# 対話継続用プロンプト
CONTINUE_DIALOGUE_PROMPT = ChatPromptTemplate.from_template(
    """あなたは、特許調査をサポートするAIアシスタントです。
    ユーザーの意図を深く理解するため、多様な切り口から調査の可能性を広げる質問を投げかけてください。
    以下の対話履歴を分析し、ユーザーが気づいていないかもしれない潜在的なニーズを掘り起こすような、**100字前後**の質問をしてください。
    
    対話履歴:
    {chat_history}

    あなたのタスク:
    1. 対話履歴から、ユーザーの調査目的の核心を推測する。
    2. その核心に基づき、調査の方向性を具体化するための選択肢を、以下の5つの異なる視点から提案する。
        - **技術の核心:** どのような技術的特徴に焦点を当てるか？（例：特定のアルゴリズム、材料、構造など）
        - **課題解決:** どのような課題を解決するための技術か？（例：効率化、コスト削減、安全性向上など）
        - **応用分野:** どのような製品やサービスへの応用を想定しているか？（例：自動運転、医療診断、製造業など）
        - **IPC分類:** 関連しそうな特許分類（IPC）は何か？（いくつか候補を挙げる）
        - **狙い（ビジネス観点）:** この調査を通じて、どのようなビジネス上の価値を得たいか？（例：新規事業のシーズ探索、競合他社の動向調査、自社技術の優位性確認など）
    3. 各選択肢の末尾に、ユーザーが考えを深めるための具体的な質問を付け加える。
    4. 最後に、ユーザーに「どの方向性で調査を深めたいか、番号で選ぶか、あるいは自由に修正・追記してください。」と促す。

    あなたの応答:"""
)

# 調査方針生成用プロンプト
GENERATE_PLAN_PROMPT = ChatPromptTemplate.from_template(
    """あなたは、特許調査の専門家です。
    以下の対話履歴から、ユーザーが本当に調査したいであろう内容の核心を捉え、
    **100字前後**で、簡潔に、かつ要点を押さえて調査方針を立案してください。
    
    対話履歴:
    {chat_history}

    生成された調査方針:"""
)

# 条件生成用プロンプト
GENERATE_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "あなたは、ユーザーとの対話履歴と調査方針から、特許検索のための構造化されたクエリ（IPCコード、キーワード）を生成する専門家です。文脈全体を考慮してください。"),
    ("human", """以下の対話履歴と調査方針を基に、特許検索クエリをJSON形式で生成してください。

    対話履歴:
    {chat_history}

    調査方針:
    {plan_text}

    あなたのタスク:
    1. 調査方針と対話履歴から、検索に最も適したキーワードを日本語と英語の両方で抽出する。
    2. 調査方針と対話履歴から、関連性の高いIPCコードを複数抽出する。""")
])

# SQL解説用プロンプト
PROMPT_EXPLAIN_SQL = ChatPromptTemplate.from_template("以下の特許検索SQLが何をしているのか、技術者でない人にも分かるように簡潔に解説してください。\n\nSQL:\n{sql}")

# 検索条件オブジェクト解説用プロンプト
PROMPT_EXPLAIN_SEARCH_QUERY = ChatPromptTemplate.from_template("以下の特許検索条件オブジェクトが何を示しているのか、技術者でない人にも分かるように簡潔に解説してください。\n\n検索条件オブジェクト:\n{search_query_json}")

# 要約用プロンプト
PROMPT_SUMMARIZE_PATENTS = ChatPromptTemplate.from_template(
    """あなたは、企業の知財部に所属する経験豊富な特許調査の専門家です。
    以下の複数の特許情報について、それぞれの要点をまとめ、全体としてどのような技術動向が読み取れるか解説してください。

    特許リスト:
    {patent_list}

    あなたのタスク:
    1. 各特許の核心技術を1〜2文で要約する。
    2. 全体を俯瞰し、共通する技術的課題や、各社のアプローチの違いなどを解説する。
    """
)

# --- LangGraph ノード定義 ---
def route_action(state: AppState) -> Literal["continue_dialogue", "generate_plan", "generate_query"]:
    print("--- Node: route_action ---")
    latest_user_input = state.chat_history[-1][1] if state.chat_history else ""
    
    # ユーザーが明示的に検索を指示した場合
    if any(keyword in latest_user_input for keyword in ["検索して", "これでいい", "OK"]):
        if state.plan_text:
            return "generate_query"
        else:
            return "generate_plan"

    # プロンプトで判断
    chain = ROUTER_PROMPT | model
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    response = chain.invoke({"chat_history": history_str, "plan_text": state.plan_text or ""}).content
    
    if 'generate_query' in response:
        return "generate_query"
    if 'generate_plan' in response:
        return "generate_plan"
    return "continue_dialogue"

def continue_dialogue(state: AppState) -> AppState:
    print("--- Node: continue_dialogue ---")
    chain = CONTINUE_DIALOGUE_PROMPT | model
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    response = chain.invoke({"chat_history": history_str}).content
    response += "\n\n調査の方向性が固まってきたら、AIが調査方針を生成します。"
    response += "現在の情報で調査方針を生成させたい場合は、『調査方針を作成して』と入力してください。"
    state.chat_history.append(("assistant", response))
    return state

def generate_plan(state: AppState) -> AppState:
    print("--- Node: generate_plan ---")
    chain = GENERATE_PLAN_PROMPT | model
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    plan = chain.invoke({"chat_history": history_str}).content
    state.plan_text = plan
    state.chat_history.append(("assistant", f"対話の内容に基づいて、以下の調査方針を生成しました。\n\n---\n**調査方針（自動生成）**\n{plan}\n---\n\n内容を確認・編集し、よろしければ『この方針で検索条件を生成』ボタンを押してください。"))
    return state

def generate_query(state: AppState) -> AppState:
    print("--- Node: generate_query ---")
    chain = GENERATE_QUERY_PROMPT | model.with_structured_output(SearchQuery)
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    state.search_query = chain.invoke({"chat_history": history_str, "plan_text": state.plan_text})
    state.chat_history.append(("assistant", "調査方針に基づいて、検索条件を生成しました。右のエリアで内容を確認・編集してください。よろしければ『検索開始』ボタンを押してください。"))
    return state


def generate_sql_and_explanation(state: AppState) -> AppState:
    """検索クエリからSQL文と解説を生成する"""
    print("--- Node: generate_sql_and_explanation ---")
    state.current_agent_node = "generate_sql_and_explanation"

    # 統一されたビルダー関数を使い、SQLとパラメータを生成
    sql, _ = build_patent_query(state.search_query)
    state.generated_sql = sql

    # 生成されたSQLをユーザー向けに解説
    chain_sql_explain = PROMPT_EXPLAIN_SQL | model
    state.sql_explanation = chain_sql_explain.invoke({"sql": sql}).content

    # 検索条件オブジェクトをユーザー向けに解説
    chain_query_explain = PROMPT_EXPLAIN_SEARCH_QUERY | model
    state.search_query_explanation = chain_query_explain.invoke({"search_query_json": state.search_query.model_dump_json(indent=2)}).content
    
    return state

def execute_search(state: AppState) -> AppState:
    print("--- Node: execute_search ---")
    state.current_agent_node = "execute_search"
    try:
        df = search_patents_in_bigquery(state.search_query)
        state.search_results = df
    except Exception as e:
        state.error = f"検索中にエラーが発生しました: {e}"
    return state

def analyze_results(state: AppState) -> AppState:
    """検索結果を分析し、調査方針との類似度を計算する"""
    print("--- Node: analyze_results ---")
    state.current_agent_node = "analyze_results"
    
    df = state.search_results
    if df is None or df.empty:
        print("分析対象の検索結果がないため、スキップします。")
        state.analyzed_results = pd.DataFrame()
        return state

    # 調査方針のテキスト（plan_text）がなければ、ユーザー入力の履歴を結合して使う
    plan_text = state.plan_text or "\n".join([msg for role, msg in state.chat_history if role == "user"])
    if not plan_text:
        state.error = "類似度計算の基準となる調査方針またはユーザー入力がありません。"
        state.analyzed_results = df # ソート前の結果を返す
        return state

    # 各セクションのテキストを準備
    titles = df["title"].fillna("").tolist()
    abstracts = df["abstract"].fillna("").tolist()
    claims = df["claims"].fillna("").tolist()

    try:
        # 調査方針と各セクションのEmbeddingを計算
        plan_embedding = embeddings_model.embed_query(plan_text)
        title_embeddings = embeddings_model.embed_documents(titles)
        abstract_embeddings = embeddings_model.embed_documents(abstracts)
        claim_embeddings = embeddings_model.embed_documents(claims)

        # コサイン類似度を計算
        sim_title = cosine_similarity([plan_embedding], title_embeddings)[0]
        sim_abstract = cosine_similarity([plan_embedding], abstract_embeddings)[0]
        sim_claims = cosine_similarity([plan_embedding], claim_embeddings)[0]

        # 重み付け平均でスコアを算出
        weights = state.similarity_weights
        score = (
            sim_title * weights.get("title", 0.4) +
            sim_abstract * weights.get("abstract", 0.4) +
            sim_claims * weights.get("claims", 0.2)
        )

        # 結果をDataFrameに追加
        analyzed_df = df.copy()
        analyzed_df["sim_title"] = sim_title
        analyzed_df["sim_abstract"] = sim_abstract
        analyzed_df["sim_claims"] = sim_claims
        analyzed_df["score"] = score
        
        # スコアで降順にソート
        state.analyzed_results = analyzed_df.sort_values(by="score", ascending=False).reset_index(drop=True)

    except Exception as e:
        state.error = f"埋め込みベクトルの計算または類似度計算中にエラーが発生しました: {e}"
        state.analyzed_results = df # ソート前の結果を返す
        
    print("分析が完了しました。")
    return state

def summarize_selected_patents(state: AppState) -> AppState:
    print("--- Node: summarize_selected_patents ---")
    state.current_agent_node = "summarize_selected_patents"
    
    if state.search_results is None or not state.selected_patents_for_summary:
        state.summary_result = "要約対象の特許が選択されていません。"
        return state

    selected_df = state.search_results[state.search_results['publication_number'].isin(state.selected_patents_for_summary)]
    
    if selected_df.empty:
        state.summary_result = "選択された特許が見つかりません。"
        return state

    patent_list_str = selected_df.to_string(index=False)
    chain = PROMPT_SUMMARIZE_PATENTS | model
    state.summary_result = chain.invoke({"patent_list": patent_list_str}).content
    return state

# --- ワークフローの構築 ---
interaction_workflow = StateGraph(AppState)
interaction_workflow.add_node("continue_dialogue", continue_dialogue)
interaction_workflow.add_node("generate_plan", generate_plan)
interaction_workflow.add_node("generate_query", generate_query)
interaction_workflow.set_conditional_entry_point(
    route_action, 
    {
        "continue_dialogue": "continue_dialogue", 
        "generate_plan": "generate_plan",
        "generate_query": "generate_query"
    }
)
interaction_workflow.add_edge("continue_dialogue", END)
interaction_workflow.add_edge("generate_plan", END) # 調査方針ができたら一旦ユーザーに返す
interaction_workflow.add_edge("generate_query", END)
interaction_app = interaction_workflow.compile()

search_execution_workflow = StateGraph(AppState)
search_execution_workflow.add_node("generate_sql_and_explanation", generate_sql_and_explanation)
search_execution_workflow.add_node("execute_search", execute_search)
search_execution_workflow.add_node("analyze_results", analyze_results)
search_execution_workflow.set_entry_point("generate_sql_and_explanation")
search_execution_workflow.add_edge("generate_sql_and_explanation", "execute_search")
search_execution_workflow.add_edge("execute_search", "analyze_results")
search_execution_workflow.add_edge("analyze_results", END)
search_execution_app = search_execution_workflow.compile()

synopsis_workflow = StateGraph(AppState)
synopsis_workflow.add_node("summarize_selected_patents", summarize_selected_patents)
synopsis_workflow.set_entry_point("summarize_selected_patents")
synopsis_workflow.add_edge("summarize_selected_patents", END)
synopsis_app = synopsis_workflow.compile()

# --- 外部から呼び出す関数 ---
def run_interaction(state: AppState) -> AppState:
    return AppState(**interaction_app.invoke(state))

def execute_patent_search_workflow(state: AppState) -> AppState:
    state.agent_node_graph = search_execution_app.get_graph().draw_mermaid()
    result_dict = search_execution_app.invoke(state)
    return AppState(**result_dict)

def run_summary_workflow(state: AppState) -> AppState:
    result_dict = synopsis_app.invoke(state)
    return AppState(**result_dict)
