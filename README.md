# VRCPost Posting Tool

VRCPost への予約投稿・ストーリー自動更新を行うデスクトップアプリケーションです。

## 機能

- **予約投稿**: 指定した日時に写真付きポストを自動投稿
- **ストーリー更新**: 指定した時間にストーリーを自動更新
- **スケジュール管理**: 繰り返し投稿（日次・週次・月次）や一括スケジュール設定
- **画像管理**: 投稿する画像のプレビュー・ドラッグ＆ドロップ対応
- **設定管理**: 接続先 URL やブラウザオプション等を GUI から変更可能
- **ログビューア**: アプリ内でリアルタイムにログを確認・フィルタ・エクスポート

## 必要要件

- Python 3.10 以上
- Google Chrome または Chromium ベースブラウザ

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/Meta-Develop/VRCPost_posting_tool.git
cd VRCPost_posting_tool

# 仮想環境を作成
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 依存パッケージをインストール
pip install -e .

# Playwright ブラウザをインストール
playwright install chromium
```

## 使い方

```bash
# GUI を起動
vrcpost-poster

# または直接実行
python -m src
```

### 初回セットアップ

1. アプリを起動すると、VRCPost のログイン画面が表示されます
2. Google アカウントまたはメールアドレスでログインしてください
3. ログイン後、セッション情報が安全に保存されます

### 予約投稿

1. 「投稿」タブを開く
2. 画像を選択（ドラッグ＆ドロップ対応）
3. テキストを入力
4. 「予約投稿」にチェックを入れ、投稿日時を設定
5. 「投稿する」ボタンをクリック

### ストーリー更新

1. 「ストーリー」タブを開く
2. ストーリー用の画像を選択
3. テキストを入力（任意）
4. 「予約更新」にチェックを入れ、更新時間を設定
5. 「アップロード」をクリック

### スケジュール管理

「スケジュール」タブで登録済みジョブの一覧を確認できます。
ジョブの選択・キャンセルも同タブから操作できます。

### 設定

「設定」タブから接続先 URL、ブラウザオプション、投稿デフォルト、
スケジューラ同時実行数などを変更できます。
設定は `config/settings.json` に保存されます。

### ログ

「ログ」タブでアプリケーションのログをリアルタイムに確認できます。
ログレベルでフィルタしたり、テキストファイルへエクスポートできます。

## 開発

```bash
# 開発用依存をインストール
pip install -e ".[dev]"

# テスト実行
python -m pytest tests/ -v

# Lint
python -m ruff check src/ tests/
```

## ライセンス

MIT License
