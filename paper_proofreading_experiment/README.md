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
- **手動修正ワークフロー**: イテレーション間でPDFファイルを手動更新可能
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

### フロントエンド (Next.js 14)

```
frontend-nextjs/
├── app/               # Next.js App Router
│   ├── layout.tsx     # ルートレイアウト
│   ├── page.tsx       # メインページ
│   └── globals.css    # グローバルスタイル
├── components/        # Reactコンポーネント
│   ├── Header.tsx
│   ├── PaperList.tsx
│   ├── PhaseControls.tsx
│   ├── Phase1Selector.tsx
│   ├── IssueCard.tsx
│   ├── LogOutput.tsx
│   └── ResetModal.tsx
├── lib/               # コアライブラリ
│   ├── store.ts       # Zustand状態管理
│   ├── api.ts         # APIクライアント
│   ├── websocket.ts   # WebSocketマネージャー
│   └── utils.ts       # ユーティリティ
└── types/             # TypeScript型定義
```

**技術スタック**:
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Zustand (状態管理)
- Axios (HTTPクライアント)
- React Hot Toast (通知)
- Lucide React (アイコン)

## 環境構築

### 必要な環境

- **Python**: 3.10以上
- **Node.js**: 18.0以上（Next.jsフロントエンド用）
- **npm** または **yarn**: パッケージマネージャー

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

### 5. Next.jsフロントエンドのセットアップ

```bash
# フロントエンドディレクトリに移動
cd frontend-nextjs

# 依存パッケージをインストール
npm install

# 開発サーバーを起動（別のターミナルで）
npm run dev
```

### 6. サーバーの起動

#### ターミナル1: バックエンドサーバー

```bash
# プロジェクトルート (paper_proofreading_experiment) から実行
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### ターミナル2: フロントエンドサーバー

```bash
# プロジェクトルートから
cd frontend-nextjs
npm run dev
```

サーバーが起動したら、ブラウザで以下にアクセス：

- **Web UI (Next.js)**: http://localhost:3000
- **API サーバー**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health


### 論文校正システム（フェーズ3特化UI）の起動

Phase3のみを運用したい場合は、FastAPIサーバーに同梱されている「論文校正システム」UIを利用できます。セッション管理や履歴表示を省いた最小構成で、TeX/PDFと除外チェックリストを指定するとLLM校正が1回だけ実行され、その場で結果を確認できます。


1. 依存関係をインストールしたプロジェクトルートでFastAPIサーバーを起動します。
   ```bash
   python run_server.py
   # または
   uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
   ```
2. ブラウザで http://localhost:8000/phase3-only を開きます。
3. 表示されるフォームに「論文ID」「TeXファイル」「PDFファイル」「除外するチェックリスト項目（任意）」を入力して「校正する」を押します。
4. LLMの校正結果（指摘一覧）がブラウザに表示され、すべての入出力は `data/phase3_only/<paper_id>/<timestamp>/` に保存されます（TeX/PDF/プロンプト/LLM応答/結果JSON）。


### 7. 本番環境でのデプロイ

#### フロントエンドのビルド

```bash
cd frontend-nextjs
npm run build
npm start
```

#### バックエンドの起動

```bash
# プロジェクトルートから
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 使い方

### 1. 論文のアップロード

1. Web UIの「論文をアップロード」ボタンをクリック
2. 論文ID、PDFファイルを選択
3. アップロードを実行

### 2. Phase1: クリーン化の実行

1. 論文リストから論文を選択
2. 「Phase1: クリーン化」ボタンをクリック
3. LLMからの指摘を確認
4. 各指摘に対してアクションを選択：
   - **[A] 承認**: 正しい指摘として記録
   - **[S] スキップ**: 誤検出として記録
   - **[Q] 中断**: 処理を中断
5. 「次のイテレーションに進みますか？」で **Y** を選択
6. 必要に応じてPDFファイルを手動で更新
7. 次のイテレーションが開始される

**注意**: PDFファイルは直接編集できないため、手動修正が必要な場合は、元のソースファイル（例：LaTeX）を編集してPDFを再生成する必要があります。

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

### 環境変数エラー

**エラー**: `ValueError: 環境変数 GOOGLE_API_KEY または GEMINI_API_KEY が設定されていません`

**解決方法**:

1. プロジェクトルートに`.env`ファイルを作成してください：
   ```bash
   cp .env.example .env
   ```

2. `.env`ファイルにAPIキーを設定：
   ```bash
   GOOGLE_API_KEY=your_actual_api_key_here
   # または
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. `python-dotenv`がインストールされているか確認：
   ```bash
   pip install -r backend/requirements.txt
   ```

4. サーバーを再起動してください

### LLM APIエラー

**エラー**: `API key not found`

**解決方法**: `.env`ファイルに正しいAPIキーが設定されているか確認してください。

### JSON Parse Error

**エラー**: `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**解決方法**: 空または破損した進捗ファイルが原因です。リセットボタンで進捗情報を削除してください。

### ImportError: attempted relative import

**エラー**: `ImportError: attempted relative import with no known parent package`

**解決方法**: バックエンドサーバーは必ずプロジェクトルート (`paper_proofreading_experiment`) から実行してください：

```bash
# 正しい方法
cd paper_proofreading_experiment
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 間違った方法（動作しません）
cd backend
python -m uvicorn main:app --reload
```

## 開発ロードマップ

### 実装済み

- ✅ Phase1セッション管理システム
- ✅ 手動修正ワークフロー
- ✅ コピーボタン
- ✅ データリセット機能
- ✅ バックエンドのモジュール化
- ✅ Pydanticによる型安全性
- ✅ Next.js 14フロントエンド（TypeScript + Tailwind CSS）
- ✅ Phase1選択ドロップダウンUI
- ✅ Zustand状態管理
- ✅ WebSocketリアルタイム通信
- ✅ レスポンシブデザイン

### 今後の改善予定

- 🚧 ダークモード対応
- 🚧 ユニットテスト・E2Eテスト
- 🚧 Docker対応
- 🚧 CI/CDパイプライン

## ライセンス

MIT License
