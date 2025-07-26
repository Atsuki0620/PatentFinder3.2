from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from ..state import SearchConditions

class BaseStrategy(ABC):
    """
    すべての検索戦略が継承する抽象基底クラス。
    """
    @abstractmethod
    def generate_sql(self, conditions: SearchConditions) -> Tuple[str, Dict[str, Any]]:
        """
        検索条件を受け取り、実行可能なSQLクエリ文字列と
        パラメータの辞書を返す。
        
        :param conditions: ユーザーが設定した検索条件
        :return: (SQLテンプレート文字列, パラメータ辞書) のタプル
        """
        pass
