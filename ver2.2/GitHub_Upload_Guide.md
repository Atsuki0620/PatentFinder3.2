# GitHubへのプロジェクトアップロード手順 (成功事例)

このドキュメントは、ローカルプロジェクトを新規GitHubリポジトリにアップロードする際の成功した手順をまとめたものです。

## 前提条件

*   Gitがインストールされており、ターミナルから利用できること。
*   GitHubに新しい空のリポジトリが作成済みであること（例: `https://github.com/Atsuki0620/PatentsFinder2.2.git`）。

## 手順

以下のコマンドをプロジェクトのルートディレクトリで順番に実行します。

### 1. Gitリポジトリの初期化

プロジェクトディレクトリをGitリポジトリとして初期化し、デフォルトブランチ名を `main` に設定します。

```bash
git init -b main
```

### 2. すべてのファイルを追加

現在のディレクトリ内のすべてのファイルとディレクトリをステージングエリアに追加します。

```bash
git add .
```

### 3. コミット

ステージングされたファイルをコミットします。コミットメッセージに特殊文字が含まれる場合や、シェルでの引用符の解釈に問題がある場合は、一時ファイルを使用する方法が確実です。

#### コミットメッセージを一時ファイルに書き込む

```bash
echo "Initial commit" > commit_message.txt
```

#### 一時ファイルを使用してコミットを実行

```bash
git commit -F commit_message.txt
```

### 4. リモートリポジトリの追加

ローカルリポジトリに、GitHub上のリモートリポジトリを追加します。`origin` はリモートリポジトリのエイリアス名です。

```bash
git remote add origin https://github.com/Atsuki0620/PatentsFinder2.1.git
```

### 5. リモート履歴との統合 (初回プッシュ時のエラー対応)

もし `git push` 時に `fatal: refusing to merge unrelated histories` エラーが発生した場合、ローカルとリモートの履歴が異なるためです。この場合、以下のコマンドでリモートの履歴をローカルに統合します。

```bash
git pull origin main --allow-unrelated-histories
```

### 6. プロジェクトをGitHubにプッシュ

ローカルの `main` ブランチの変更をリモートの `origin` リポジトリにプッシュし、`main` ブランチを追跡するように設定します。

```bash
git push -u origin main
```

---

これで、プロジェクトがGitHubに正常にアップロードされます。
