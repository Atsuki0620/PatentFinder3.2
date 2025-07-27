# GEMINI.md

## プロジェクトの全体像

### システム構成図
- フロントエンド：Streamlit Web UI（サイドバー：APIキー設定／メイン画面：検索条件入力・結果表示・ダウンロード・要約表示）
- バックエンド：Python（Streamlit, pandas, google-cloud-bigquery, OpenAI API）
- データベース：Google BigQuery（patents-public-data.patents.publications）

### ディレクトリ構造
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
PatentsFinder_DesignGuide.md # 詳細設計書
```

### ドメイン用語
- IPCコード：国際特許分類コード
- LLM：大規模言語モデル（GPT-4等）
- Embeddings：ベクトル化による類似度計算
- SearchQuery：検索条件をまとめたオブジェクト

---

## 絶対に守る開発規約
- React利用時は関数コンポーネントのみ（本PJでは未使用）
- SQLは必ずプレースホルダ（パラメータ化）で実装し、直接値埋め込み禁止
- APIキーや認証情報はコード・リポジトリに絶対に含めない
- Python仮想環境（venv）を必ず作成し、依存パッケージはrequirements.txtで管理.
- 仮想環境名はenv-PatentsFinder2.1
- 依存ライブラリは事前に許可リストで承認されたもののみ利用
- コードレビューはPR（Pull Request）で必須

---

## セキュリティ・コンプライアンス要件
- 個人情報は一切扱わない（特許データは公開情報のみ）
- 依存ライブラリは公式・信頼性の高いもののみ利用
- 脆弱性チェックはpip-audit等で定期実施
- APIキー・認証情報は環境変数で管理し、ファイル・リポジトリに残さない
- 外部API利用時は利用規約・プライバシーポリシーを遵守

---

## 実行環境ポリシー
- Pythonプロジェクトは必ず `python -m venv [PJ名称]` で仮想環境を作成
- 依存パッケージは `pip install -r requirements.txt` でインストール
- Docker利用時はalpineベースイメージを推奨
- .envファイルはgit管理対象外とする

---

## テスト／CIルール
- すべてのPR（Pull Request）はpytestによるテストを必須
- テスト未通過の場合はマージ・push禁止
- テストコードは `tests/` ディレクトリに配置
- CIツール（GitHub Actions等）で自動テスト・脆弱性チェックを実施

---

## ドキュメント生成規格
- API仕様はOpenAPI v3で記述
- UIコンポーネント設計はStorybook（ファイル名規則：`*.stories.md`）
- 設計書・規約はMarkdownで管理し、主要項目ごとに見出し（##）を付与
- 長文化する場合は別Markdownに分割し、リンクを記載

---

## ベストプラクティスまとめ
- GEMINI.mdは“不変の憲法”として運用
- 具体的な作業指示は対話プロンプトで管理
- 大項目ごとに見出し（##）を付与し、短くモジュール化
- コードと同じくGitでバージョン管理し、PRで変更理由を明示
- セキュリティレベルに応じてtierを選択
- 機微情報はAPIキー課金ティアで管理（free tierでは絶対に記載しない）
- Sprint終了時に規約と実装の乖離チェックを必ず実施

---

## 参考リンク
- [DesignGuide.md](DesignGuide.md)
- [README.md](README.md)
