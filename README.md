# PatentFinder 3.2

AIとの対話を通じて、専門家でなくても質の高い特許調査を可能にするためのWebアプリケーションです。

## 概要

自然言語で調査したい技術内容を入力するだけで、AIがキーワードや特許分類（IPC）を提案し、Google BigQueryの公開特許データセットを検索するための高精度なSQLクエリを自動生成します。v3.2ではUI/UXを全面的に刷新し、検索結果の分析・可視化機能を追加することで、より直感的で実用的なアプリケーションを目指しています。

## 主な機能

-   **対話による検索条件構築**: AIとのチャットを通じて、調査の核となる「主語」と「述語」を特定し、検索条件を具体化します。
-   **動的なSQLクエリ生成**: 決定した検索条件に基づき、最適なBigQuery用SQLクエリとその解説を自動生成します。
-   **検索結果の可視化**: 検索結果から、出願年次推移や主要出願人ランキングなどのグラフを自動で描画します。
-   **AIによるサマリーレポート**: 選択した複数の特許について、AIが要点をまとめたサマリーレポートを生成・表示・ダウンロードできます。

## 実行方法

### 1. 前提条件

-   Python 3.9以上
-   Google Cloud Platform (GCP) アカウントおよびサービスアカウントキー (JSON形式)
-   OpenAI APIキー

### 2. セットアップ

1.  **リポジトリのクローンと移動**
    ```bash
    git clone [リポジトリURL]
    cd [リポジトリ名]
    ```

2.  **仮想環境の作成と有効化**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **依存ライブラリのインストール**
    ```bash
    pip install -r requirements.txt
    ```

4.  **.envファイルの作成**
    プロジェクトルートに`.env`ファイルを作成し、ご自身のAPIキーなどを記述してください。
    ```
    # OpenAI API Key
    OPENAI_API_KEY="sk-..."

    # GCP Service Account JSON (Base64 Encoded)
    # JSONファイルの中身をコピーし、Base64エンコードした文字列を貼り付けてください
    GOOGLE_APPLICATION_CREDENTIALS_JSON_BASE64="..."
    ```

### 3. アプリケーションの起動

```bash
streamlit run src/app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。アプリケーションをお楽しみください。
