# PatentFinder 3.2 設計・実装ガイド

## 1. 開発目標
v3.1の検索ロジックの知見を活かし、UI/UXを刷新した拡張性の高いWebアプリケーションを完成させる。

## 2. ディレクトリ構造
```
.
├── .streamlit/
│   └── config.toml
├── docs/
│   ├── DesignGuide3.2.md
│   ├── GEMINI.md
│   └── history.md
├── src/
│   ├── app.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── bq_client.py
│   │   ├── state.py
│   │   └── strategies/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── default.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── sidebar.py
│   │   └── main_view.py
│   └── utils/
│       ├── __init__.py
│       └── config.py
├── outputs/
│   └── .gitkeep
├── tests/
│   └── .gitkeep
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## 3. 開発フェーズとタスク

### フェーズ1: 基盤設計とUIモックアップ

-   [ ] **Task 1.1**: 上記ディレクトリ構造を実際にファイルシステム上に作成する。
-   [ ] **Task 1.2**: `requirements.txt` に `streamlit`, `openai`, `google-cloud-bigquery`, `pandas`, `plotly` を記述する。
-   [ ] **Task 1.3**: `src/core/state.py` に `AppState` データクラスを定義する。最低限、`chat_history`, `search_conditions`, `search_results` などの属性を持たせる。
-   [ ] **Task 1.4**: `src/app.py` の骨格を作成。`AppState` を初期化し、`src/ui/sidebar.py` と `src/ui/main_view.py` を呼び出すだけのシンプルな構成にする。
-   [ ] **Task 1.5**: `src/ui/` 以下に、表示のみを行うプレースホルダー的なUIコンポーネントを作成し、3カラムレイアウトが機能することを確認する。

### フェーズ2: 対話型検索フローの実装

-   [ ] **Task 2.1**: `src/core/agent.py` に `extract_subject_predicate(user_query)` 関数を実装する。内部でLLMを呼び出し、ユーザーの初回入力から「主語」と「述語」をJSON形式で抽出する。
-   [ ] **Task 2.2**: `agent.py` に `suggest_terms(subject, predicate)` 関数を実装する。主語・述語に基づき、関連キーワードとIPC分類をLLMに提案させる。
-   [ ] **Task 2.3**: `src/ui/main_view.py` を更新し、ユーザーが入力したクエリを `agent` に渡し、返ってきたキーワード・IPC候補をチェックボックスで表示・選択できるようにする。
-   [ ] **Task 2.4**: `src/core/strategies/base.py` に `BaseStrategy` 抽象クラスを定義し、`generate_sql(conditions)` メソッドを持たせる。
-   [ ] **Task 2.5**: `src/core/strategies/default.py` に `SubjectPredicateStrategy` クラスを実装し、v3.1で実績のある `WHERE (主語) AND (述語)` 形式のパラメータ化SQLクエリを生成するロジックを記述する。

### フェーズ3: 検索実行と結果の可視化

-   [ ] **Task 3.1**: `requirements.txt` に `scikit-learn` を追加する（類似度計算のため）。
-   [ ] **Task 3.2**: `src/core/state.py` の `SearchConditions` に `start_date`, `end_date`, `countries`, `limit` 属性を追加する。
-   [ ] **Task 3.3**: `src/ui/main_view.py` に、期間・国・件数を指定するためのUIコンポーネントを追加し、`AppState` と連携させる。SQL表示を `st.expander` に変更する。
-   [ ] **Task 3.4**: `src/core/strategies/default.py` の `generate_sql` を修正し、期間・国・件数の条件をSQLクエリに反映させる。また、SQLをインデント付きで整形する。
-   [ ] **Task 3.5**: `src/core/agent.py` の `run_search` ワークフローを大幅に改修する。
    -   `st.status` を用いて、処理の進行状況を段階的に表示する。
    -   日本語キーワードを英語に翻訳するステップを追加する。
    -   BigQuery検索後、結果（タイトル・要約）と調査方針をEmbedding化する。
    -   コサイン類似度を計算し、結果をランキングソートする。
-   [ ] **Task 3.6**: `src/core/bq_client.py` を実装し、BigQueryへの接続とクエリ実行をカプセル化する。
-   [ ] **Task 3.7**: （TBD）`src/core/visualize.py` を作成し、DataFrameから出願年次推移グラフなどを生成する関数を実装する。
-   [ ] **Task 3.8**: （TBD）`src/core/reporter.py` を作成し、選択された特許の要約をLLMに依頼する関数を実装する。