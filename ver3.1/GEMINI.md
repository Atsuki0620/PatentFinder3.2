# PatentFinder3.1 プロジェクト概要

## 目的

AIとの対話を通じて、専門家でなくても質の高い特許調査を可能にするためのコマンドラインツールを開発する。最終的なアウトプットは、Google BigQueryの公開特許データセットを検索するための高精度なSQLクエリ、及びそれに基づいた調査レポートである。

## 主要ファイル

-   `patent_search_script.py`: メインとなる対話型検索スクリプト。
-   `corded-guild-459506-i6-5bc162f91e16.json`: Google Cloudのサービスアカウントキー。BigQueryへの接続に必須。
-   `docs/`: 開発経緯やサマリーを格納するドキュメントフォルダ。
-   `investigations/`: 各調査のレポートが格納されるフォルダ。

## 実行方法

1.  **仮想環境のアクティベート:**
    ```bash
    .\env-PatentsFinder3.1\Scripts\activate
    ```
2.  **メインスクリプトの実行:**
    ```bash
    python patent_search_script.py
    ```

## 技術スタック

-   **言語:** Python
-   **LLM:** OpenAI API (gpt-4-turbo)
-   **データベース:** Google BigQuery
-   **主要ライブラリ:** `openai`, `google-cloud-bigquery`
