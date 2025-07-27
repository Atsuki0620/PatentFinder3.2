# PatentsFinder2.0

## 概要

技術内容から関連特許を検索・分析・解説するWebアプリケーションです。専門知識がなくても、AI（LLM・Embeddings）とBigQueryを活用し、技術動向や関連特許を効率的に把握できます。

## 主な特徴
- 技術内容からIPCコード・キーワードを自動抽出
- BigQueryによる高速特許検索
- AIによる類似度分析・要約生成
- 柔軟な検索条件（IPCコード・国コード・出願人・公開日・キーワード）
- 検索結果のCSVダウンロード・上位特許の要約表示

## セットアップ手順

1. 仮想環境を作成し、アクティベートします。
    ```bash
    python -m venv env-PatentsFinder2.1
    .\env-PatentsFinder2.1\Scripts\activate  # Windows
    ```
2. 必要なライブラリをインストールします。
    ```bash
    pip install -r src/requirements.txt
    ```
3. `.env`ファイルを作成し、APIキー（OpenAI, Google Cloud）を設定します。
    `.env.example`を参考にしてください。
4. Streamlitアプリケーションを起動します。
    ```bash
    streamlit run src/app.py
    ```

## セキュリティ・開発規約
- APIキーや認証情報は絶対にリポジトリに含めないでください
- SQLは必ずパラメータ化（プレースホルダ）で実装
- 依存ライブラリはrequirements.txtで管理
- 仮想環境（venv）を必ず利用
- テストはpytestで実施し、PR時に必須
- 機微情報はfree tierでは記載禁止

## ディレクトリ構成（抜粋）
```
src/
  app.py           # Streamlitアプリ本体
  core/
    agent.py       # 検索クエリ生成・ワークフロー管理
    tools.py       # BigQuery検索ロジック
    state.py       # 検索クエリ・状態管理
  utils/
    config.py      # APIキー・認証情報管理
requirements.txt   # 依存パッケージ
README.md          # プロジェクト概要
PatentsFinder_Design.md # 詳細設計書
GEMINI.md          # 開発規約・運用方針
```

## 参考リンク
- [GEMINI.md](GEMINI.md)
- [DesignGuide.md](DesignGuide.md)
