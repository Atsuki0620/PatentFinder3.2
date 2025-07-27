from typing import List, Optional, Tuple, Any, Literal
import pandas as pd
from pydantic import BaseModel, Field

# class IPCCode(BaseModel):
#     """IPCコードとその説明"""
#     code: str = Field(description="IPCコード。例: G06F 16/00")
#     description: str = Field(description="AIによって生成されたIPCコードの日本語による説明。")

class SearchQuery(BaseModel):
    """検索クエリの構造"""
    # ipc_codes: List[IPCCode] = Field(default_factory=list, description="技術内容から抽出したIPCコードと、その日本語解説のリスト。")
    ipc_codes: List[str] = Field(default_factory=list, description="技術内容から抽出したIPCコードのリスト。") # 変更
    keywords: List[str] = Field(default_factory=list, description="技術内容から抽出した、特許検索に有効なキーワード。")
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    country_codes: Optional[List[str]] = None
    assignees: Optional[List[str]] = None
    limit: int = Field(100, description="検索件数の上限")

class AppState(BaseModel):
    """
    Streamlitアプリケーション全体のセッション状態を管理する。
    """
    chat_history: List[Tuple[str, str]] = Field(default_factory=list, description="LLMとの対話履歴 (user, assistant)")
    plan_text: Optional[str] = Field(None, description="ユーザーとの対話から生成された調査方針テキスト") # 追加
    search_query: SearchQuery = Field(default_factory=SearchQuery)
    
    # 検索実行後のフィールド
    search_results: Optional[pd.DataFrame] = None
    analyzed_results: Optional[pd.DataFrame] = Field(None, description="類似度分析後の検索結果")
    summary: Optional[str] = None
    error: Optional[str] = None

    # 類似度計算の重み
    similarity_weights: dict = Field(default_factory=lambda: {"title": 0.4, "abstract": 0.4, "claims": 0.2}, description="類似度計算の重み")

    # 追加フィールド
    generated_sql: str = Field("", description="実行用に生成されたSQL文")
    sql_explanation: str = Field("", description="AIによるSQLの自然言語説明")
    search_query_explanation: str = Field("", description="AIによる検索条件オブジェクトの自然言語説明")
    agent_node_graph: Optional[str] = Field(None, description="Mermaid形式のエージェントワークフローグラフ")
    current_agent_node: Optional[str] = Field(None, description="現在実行中のエージェントノード")

    # 要約関連の追加フィールド
    selected_patents_for_summary: List[str] = Field(default_factory=list, description="要約対象としてユーザーが選択した特許文献のpublication_number")
    summary_result: str = Field("", description="選択された特許文献の要約結果")

    # 表示言語の追加フィールド
    display_language: Literal["ja", "en"] = Field("ja", description="検索結果の表示言語 (ja: 日本語, en: 英語)")

    class Config:
        arbitrary_types_allowed = True