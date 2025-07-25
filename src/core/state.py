from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
import pandas as pd
from datetime import date

@dataclass
class SearchConditions:
    """検索条件を保持するデータクラス"""
    subject_keywords: List[str] = field(default_factory=list)
    subject_ipc: List[str] = field(default_factory=list)
    predicate_keywords: List[str] = field(default_factory=list)
    predicate_ipc: List[str] = field(default_factory=list)
    
    # 高度な検索条件
    start_date: date = None
    end_date: date = None
    countries: List[str] = field(default_factory=lambda: ['US', 'JP', 'EP', 'WO', 'CN'])
    limit: int = 100

@dataclass
class AppState:
    """
    StreamlitのSessionStateで管理するアプリケーション全体の状態。
    """
    # --- 対話の状態 ---
    chat_history: List[Tuple[str, str]] = field(default_factory=list)
    
    # --- ワークフローの状態 ---
    proposed_plans: List[str] = field(default_factory=list)
    plan_text: str = ""
    terms_suggested: bool = False

    # --- 検索条件と結果 ---
    search_conditions: SearchConditions = field(default_factory=SearchConditions)
    generated_sql: str = ""
    sql_explanation: str = ""
    search_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # --- その他 ---
    error_message: str = ""
