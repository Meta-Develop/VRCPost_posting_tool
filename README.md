# VRCPost Posting Tool

VRCPost への予約投稿・ストーリー自動更新を行うデスクトップアプリケーションです。

## 機能

- **予約投稿**: 指定した日時に写真付きポストを自動投稿
- **ストーリー更新**: 指定した時間にストーリーを自動更新
- **スケジュール管理**: 繰り返し投稿や一括スケジュール設定
- **画像管理**: 投稿する画像のプレビュー・管理機能

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
python -m src.gui.main_window
```

### 初回セットアップ

1. アプリを起動すると、VRCPost のログイン画面が表示されます
2. Google アカウントまたはメールアドレスでログインしてください
3. ログイン後、セッション情報が安全に保存されます

### 予約投稿

1. 「新規投稿」タブを開く
2. 画像を選択（ドラッグ＆ドロップ対応）
3. テキストを入力（#ハッシュタグ、@メンション対応）
4. 投稿日時を設定
5. 「予約」ボタンをクリック

### ストーリー更新

1. 「ストーリー」タブを開く
2. ストーリー用の画像を選択
3. 更新時間を設定
4. 「スケジュール設定」をクリック

## 設定

設定ファイルは `config/settings.json` に保存されます。

## ライセンス

MIT License
