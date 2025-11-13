# 論文校正実験システム

学術論文の校正実験を行うためのWebベースシステムです。LLMを活用して、論文のクリーン化、誤り埋め込み、校正の3つのフェーズを実行します。

## 📋 目次

- [システム概要](#システム概要)
- [機能](#機能)
- [アーキテクチャ](#アーキテクチャ)
- [環境構築](#環境構築)
- [使い方](#使い方)
- [API仕様](#api仕様)
- [トラブルシューティング](#トラブルシューティング)

## システム概要

このシステムは、学術論文の校正精度を測定するための実験環境を提供します。

### 3つのフェーズ

1. **Phase1: クリーン化**
   - LLMを使用して論文の誤りを検出・修正
   - イテレーティブな校正プロセス
   - 手動修正のサポート
   - 各Phase1実行に固有のIDを付与

2. **Phase2: 誤り埋め込み**
   - クリーン化された論文に意図的に誤りを埋め込む
   - チェックリストに基づいた誤り生成

3. **Phase3: 校正**
   - 埋め込まれた誤りを検出
   - 検出率を測定・評価

## 機能

### ✨ 主要機能

- **Phase1セッション管理**: 各Phase1実行に固有のIDを付与し、履歴を保存
- **手動修正ワークフロー**: イテレーション間でTeXファイルを手動編集可能
- **コピーボタン**: 修正前/後の文を1クリックでクリップボードにコピー
- **データリセット**: 実験データを選択的に削除
- **WebSocket通信**: リアルタイムな進捗表示
- **CSV/JSON出力**: 実験結果の詳細なログ

### 🔧 対応LLM

- Google Gemini (gemini-1.5-pro など)
- Anthropic Claude (claude-3-opus など)

## アーキテクチャ

### バックエンド (Python/FastAPI)

```
backend/
├── core/              # 設定と依存性注入
│   ├── config.py      # アプリケーション設定
│   └── dependencies.py # 依存性注入
├── models/            # Pydanticモデル
│   ├── requests.py    # リクエストモデル
│   └── responses.py   # レスポンスモデル
├── routers/           # APIルーター
│   ├── papers.py      # 論文管理
│   └── data.py        # データ管理
├── api.py             # WebSocket通信
└── main.py            # FastAPIアプリケーション
```

### フロントエンド

- **現在**: HTML/CSS/JavaScript (Bootstrap 5)
- **次期**: Next.js 14 (App Router) + TypeScript + Tailwind CSS

## 環境構築

### 必要な環境

- **Python**: 3.10以上
- **Node.js**: 18.0以上（Next.jsフロントエンド用、将来）
- **LaTeX**: pdflatex（論文コンパイル用、オプション）

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd Graduation_Research_Experiments/paper_proofreading_experiment
```

### 2. Python環境のセットアップ

#### 仮想環境の作成

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 依存パッケージのインストール

```bash
# バックエンドの依存関係
pip install -r backend/requirements.txt

# srcの依存関係
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env`ファイルをプロジェクトルートに作成：

```bash
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key_here

# Anthropic Claude API
ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 4. 設定ファイルの確認

`config/settings.yaml`でLLMプロバイダーとモデルを設定：

```yaml
llm:
  provider: "gemini"  # or "claude"
  model: "gemini-1.5-pro"  # or "claude-3-opus-20240229"
```

### 5. サーバーの起動

```bash
# バックエンドサーバーを起動
cd backend
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

サーバーが起動したら、ブラウザで以下にアクセス：

- **Web UI**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 使い方

### 1. 論文のアップロード

1. Web UIの「論文をアップロード」ボタンをクリック
2. 論文ID、PDFファイル、TeXファイルを選択
3. アップロードを実行

### 2. Phase1: クリーン化の実行

1. 論文リストから論文を選択
2. 「Phase1: クリーン化」ボタンをクリック
3. LLMからの指摘を確認
4. 各指摘に対してアクションを選択：
   - **[M] 手動修正**: TeXファイルを手動で編集
   - **[S] スキップ**: 誤検出として記録
   - **[D] 判断困難**: 除外リストに追加
   - **[Q] 中断**: 処理を中断
5. 「次のイテレーションに進みますか？」で **Y** を選択
6. 手動でTeXファイルを編集（必要に応じて）
7. 次のイテレーションが開始される

**重要**: 「次のイテレーションに進みますか？」のダイアログが表示されている間に、TeXファイルを編集できます。Yを選択すると、編集内容が次のイテレーションに反映されます。

### 3. データのリセット

不要なデータを削除する場合：

1. Navbarの「リセット」ボタンをクリック
2. 削除する項目を選択：
   - 実験結果データ (CSV, JSON)
   - 論文バージョン履歴
   - 進捗情報
3. 「データを削除」で確定

## API仕様

### RESTful API

#### 論文管理

- `GET /api/papers/` - 論文リストを取得
- `POST /api/papers/upload` - 論文をアップロード
- `GET /api/papers/{paper_id}/info` - 論文情報を取得

#### データ管理

- `POST /api/data/reset` - データをリセット
- `GET /api/data/phase1_sessions/{paper_id}` - Phase1セッション履歴を取得
- `GET /api/data/iterations/{paper_id}` - イテレーション履歴を取得
- `GET /api/data/detection_rate/{paper_id}` - 検出率を取得

### WebSocket API

- `/ws/{client_id}` - WebSocket接続
- `/ws/{client_id}/action` - ユーザーアクション送信

## トラブルシューティング

### LLM APIエラー

**エラー**: `API key not found`

**解決方法**: `.env`ファイルに正しいAPIキーが設定されているか確認してください。

### JSON Parse Error

**エラー**: `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**解決方法**: 空または破損した進捗ファイルが原因です。リセットボタンで進捗情報を削除してください。

## 開発ロードマップ

### 実装済み

- ✅ Phase1セッション管理システム
- ✅ 手動修正ワークフロー
- ✅ コピーボタン
- ✅ データリセット機能
- ✅ バックエンドのモジュール化
- ✅ Pydanticによる型安全性

### 近日実装予定

- 🚧 Next.jsフロントエンド（TypeScript + Tailwind CSS）
- 🚧 Phase1選択ドロップダウンUI
- 🚧 sessions.jsonからphase1_sessions.jsonへの完全移行

## ライセンス

MIT License
