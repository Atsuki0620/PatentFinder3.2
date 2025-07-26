# -*- coding: utf-8 -*-
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# --- プロジェクトルートをPythonパスに追加 ---
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# --- プロジェクトモジュールのインポート ---
from src.core.state import SearchConditions
from src.core.strategies.default import SubjectPredicateStrategy
from src.core import bq_client
from src.core.bq_client import BQClientError
from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter

# --- グローバル設定 ---
CONFIG_PATH = project_root / "tests" / "config.json"
LOG_DIR = project_root / "tests" / "logs"

def setup_logging(log_dir: Path) -> None:
    """ログ設定を初期化する"""
    log_dir.mkdir(exist_ok=True)
    log_filename = f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = log_dir / log_filename

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"ログファイルを次の場所に作成しました: {log_filepath}")

def load_config(config_path: Path) -> dict:
    """設定ファイルを読み込む"""
    if not config_path.exists():
        logging.error(f"設定ファイルが見つかりません: {config_path}")
        logging.error("config.json.template をコピーして config.json を作成し、内容を編集してください。")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if "gcp_service_account_path" not in config or not config["gcp_service_account_path"]:
        logging.error("設定ファイルに gcp_service_account_path が指定されていません。")
        sys.exit(1)
        
    return config

def load_gcp_credentials(gcp_sa_path_str: str) -> dict:
    """GCPサービスアカウントのJSONキーファイルを読み込む"""
    gcp_sa_path = Path(gcp_sa_path_str)
    if not gcp_sa_path.is_absolute():
        gcp_sa_path = project_root / gcp_sa_path_str

    if not gcp_sa_path.exists():
        logging.error(f"GCPサービスアカウントキーファイルが見つかりません: {gcp_sa_path}")
        sys.exit(1)
    
    with open(gcp_sa_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    """テストランナーのメイン処理"""
    setup_logging(LOG_DIR)
    config = load_config(CONFIG_PATH)
    gcp_credentials = load_gcp_credentials(config["gcp_service_account_path"])

    logging.info("--- テスト開始 ---")

    test_conditions = SearchConditions(
        subject_keywords=["semiconductor", "manufacturing"],
        subject_ipc=["H01L"],
        predicate_keywords=["defect", "inspection"],
        predicate_ipc=[],
        countries=["US", "JP"], # 複数の国でテスト
        limit=20
    )
    logging.info(f"使用する検索条件:\n{test_conditions}")

    strategy = SubjectPredicateStrategy()
    try:
        sql, params = strategy.generate_sql(test_conditions)
        logging.info("--- 生成されたSQL ---")
        logging.info(sql)
        logging.info("--- SQLパラメータ ---")
        
        param_info = {}
        for p in params:
            if isinstance(p, ScalarQueryParameter):
                param_info[p.name] = {'type': p.type_, 'value': p.value}
            elif isinstance(p, ArrayQueryParameter):
                param_info[p.name] = {'type': f'ARRAY<{p.array_type}>', 'value': p.values}
            else:
                param_info[p.name] = {'type': 'Unknown', 'value': str(p)}
        
        logging.info(json.dumps(param_info, indent=2, ensure_ascii=False))

    except Exception as e:
        logging.error(f"SQLの生成中にエラーが発生しました: {e}", exc_info=True)
        return

    logging.info("--- BigQuery検索開始 ---")
    try:
        results_df = bq_client.execute_query(sql, params, credentials_info=gcp_credentials)
        logging.info("--- 検索成功 ---")
        logging.info(f"{len(results_df)}件の特許が見つかりました。")
        if not results_df.empty:
            logging.info("--- 結果のプレビュー (先頭5件) ---")
            logging.info("\n" + results_df.head().to_string())

    except BQClientError as e:
        logging.error("BigQueryの検索中にエラーが発生しました。", exc_info=True)
    
    except Exception as e:
        logging.error("予期せぬエラーが発生しました。", exc_info=True)

    logging.info("--- テスト終了 ---")


if __name__ == "__main__":
    main()
