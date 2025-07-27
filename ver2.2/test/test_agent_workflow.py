
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.state import AppState, SearchQuery
from core.agent import run_interaction

class TestAgentWorkflow(unittest.TestCase):

    def setUp(self):
        """Set up a mock environment for testing."""
        # Mock the OpenAI and other external dependencies
        self.model_patcher = patch('core.agent.model')
        self.mock_model = self.model_patcher.start()
        
        self.embeddings_patcher = patch('core.agent.embeddings_model')
        self.mock_embeddings = self.embeddings_patcher.start()

    def tearDown(self):
        """Clean up the patches."""
        self.model_patcher.stop()
        self.embeddings_patcher.stop()

    def test_full_interaction_flow(self):
        """
        Test the complete agent workflow from initial chat to query generation.
        """
        # 1. Initial state
        app_state = AppState()

        # 2. First user input -> should continue dialogue
        app_state.chat_history.append(("user", "AIを使った自動運転技術について調べています。"))
        
        # Mock the router to return 'continue_dialogue'
        self.mock_model.invoke.return_value.content = "continue_dialogue"
        updated_state = run_interaction(app_state)
        
        self.assertIn("もう少し詳しく教えていただけますか？", updated_state.chat_history[-1][1])
        self.assertEqual(len(updated_state.plan_suggestions), 0)
        self.assertEqual(updated_state.plan_text, "")

        # 3. Second user input -> should generate initial plan
        updated_state.chat_history.append(("user", "特に、カメラ映像をAIで解析して、歩行者を検知する技術に興味があります。"))
        
        # Mock the router to return 'generate_plan'
        self.mock_model.invoke.return_value.content = "カメラ映像をAIで解析し、歩行者を検知する自動運転技術に関する特許調査。"
        with patch('core.agent.route_action', return_value='generate_plan'):
             updated_state = run_interaction(updated_state)

        self.assertIn("【調査方針案】", updated_state.chat_history[-1][1])
        self.assertTrue(len(updated_state.plan_text) > 0)

        # 4. User asks for other suggestions -> should suggest alternative plans
        updated_state.chat_history.append(("user", "別の案もお願いします。"))
        
        # Mock the router to return 'suggest_alternative_plans'
        self.mock_model.invoke.return_value.content = """
- 1. LIDARセンサーとカメラ映像を融合させた歩行者検知技術
- 2. 夜間や悪天候下での歩行者検知精度を向上させる技術
- 3. 歩行者の行動予測（飛び出しなど）を行うAI技術
- 4. 車載コンピューティングの負荷を低減する効率的なAIアルゴリズム
- 5. 収集したデータを活用してAIモデルを継続的に改善する手法
上記1〜5でご希望のものを選択してください。もし、ご希望の調査方針と異なる場合は、修正点を具体的に記述してください。
"""
        with patch('core.agent.route_action', return_value='suggest_alternative_plans'):
            updated_state = run_interaction(updated_state)

        self.assertIn("【調査方針の再提案】", updated_state.chat_history[-1][1])
        self.assertEqual(len(updated_state.plan_suggestions), 5)

        # 5. User chooses a plan and says "進めて" -> should generate query
        updated_state.chat_history.append(("user", "3番で進めてください。"))
        updated_state.selected_plan = "歩行者の行動予測（飛び出しなど）を行うAI技術"
        
        # Mock the router to return 'generate_query'
        mock_search_query = SearchQuery(
            keywords=["歩行者検知", "行動予測", "AI", "自動運転"],
            ipc_codes=["G06T 7/00", "G06V 20/58"]
        )
        self.mock_model.with_structured_output.return_value.invoke.return_value = mock_search_query
        with patch('core.agent.route_action', return_value='generate_query'):
            final_state = run_interaction(updated_state)

        self.assertIn("検索条件を生成しました", final_state.chat_history[-1][1])
        self.assertEqual(final_state.search_query.keywords, ["歩行者検知", "行動予測", "AI", "自動運転"])
        self.assertEqual(final_state.search_query.ipc_codes, ["G06T 7/00", "G06V 20/58"])


if __name__ == '__main__':
    unittest.main()
