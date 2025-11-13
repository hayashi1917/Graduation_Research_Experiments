# Paper Proofreading Experiment - Frontend

Next.js 14ベースのモダンなWeb UIフロントエンド

## 技術スタック

- **Next.js 14** - App Routerを使用したReactフレームワーク
- **TypeScript** - 型安全な開発
- **Tailwind CSS** - ユーティリティファーストCSSフレームワーク
- **Zustand** - 軽量な状態管理ライブラリ
- **Axios** - HTTPクライアント
- **WebSocket** - リアルタイム通信
- **React Hot Toast** - トースト通知
- **Lucide React** - アイコンライブラリ

## プロジェクト構造

```
frontend-nextjs/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # ルートレイアウト
│   ├── page.tsx           # メインページ
│   └── globals.css        # グローバルスタイル
├── components/            # Reactコンポーネント
│   ├── Header.tsx         # ヘッダー（リセットボタン付き）
│   ├── PaperList.tsx      # 論文リスト
│   ├── PaperUploadModal.tsx  # 論文アップロードモーダル
│   ├── PhaseControls.tsx  # Phase実行コントロール
│   ├── Phase1Selector.tsx # Phase1セッション選択
│   ├── IssueCard.tsx      # 指摘事項カード（コピーボタン付き）
│   ├── LogOutput.tsx      # ログ出力
│   └── ResetModal.tsx     # リセットモーダル
├── lib/                   # コアライブラリ
│   ├── store.ts           # Zustand状態管理
│   ├── api.ts             # APIクライアント
│   ├── websocket.ts       # WebSocketマネージャー
│   └── utils.ts           # ユーティリティ関数
├── types/                 # TypeScript型定義
│   └── index.ts           # 共通型定義
├── package.json           # 依存関係
├── tsconfig.json          # TypeScript設定
├── tailwind.config.ts     # Tailwind CSS設定
└── next.config.js         # Next.js設定（APIプロキシ）
```

## セットアップ

### 前提条件

- Node.js 18.x以上
- npm または yarn

### インストール

```bash
# ディレクトリに移動
cd paper_proofreading_experiment/frontend-nextjs

# 依存関係をインストール
npm install
```

## 開発

### 開発サーバーを起動

```bash
npm run dev
```

ブラウザで http://localhost:3000 を開く

### ビルド

```bash
npm run build
```

### 本番環境で起動

```bash
npm start
```

## 主な機能

### 1. 論文管理
- 論文のリスト表示
- 論文の選択
- 論文のアップロード（PDF + TeX）

### 2. Phase実行
- Phase 1（初回校正）
- Phase 2（埋め込み誤り検出）
- Phase 3（クリーン化）
- リアルタイム実行状態の表示

### 3. Phase1セッション選択
- Phase2/3実行時にPhase1セッションを選択
- セッションのステータス表示（完了/実行中/中止）
- セッション情報（開始時刻、完了時刻、Iteration数）

### 4. 指摘事項表示
- 修正前の文
- 理由
- 修正後の文
- 各フィールドのワンクリックコピーボタン

### 5. ログ出力
- ターミナル風のログ表示
- タイムスタンプ付き
- ログレベル別の色分け（info/warning/error/success）
- 自動スクロール

### 6. データリセット
- 実験結果の削除
- バージョン履歴の削除
- 進捗情報の削除
- 選択的な削除が可能

## API統合

Next.js設定でバックエンドAPIをプロキシ:

```javascript
// next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
    {
      source: '/ws/:path*',
      destination: 'http://localhost:8000/ws/:path*',
    },
  ];
}
```

## 状態管理

Zustandを使用した軽量な状態管理:

```typescript
interface AppState {
  selectedPaper: Paper | null;
  papers: Paper[];
  phase1Sessions: Phase1Session[];
  selectedPhase1: Phase1Session | null;
  currentPhase: string | null;
  currentIssue: ProofreadingIssue | null;
  logs: LogEntry[];
  // ... setters
}
```

## WebSocket通信

リアルタイム通信用のWebSocketマネージャー:

- 自動再接続（最大5回）
- メッセージハンドラーの登録
- Phase実行の制御
- ユーザーアクションの送信

## スタイリング

Tailwind CSSを使用したレスポンシブデザイン:

- モバイル対応
- ダークモード対応（将来実装予定）
- カスタムカラーパレット
- カスタムスクロールバー
- アニメーション（fade-in）

## トラブルシューティング

### ポート3000が使用中の場合

```bash
# 別のポートで起動
PORT=3001 npm run dev
```

### ビルドエラーが発生する場合

```bash
# node_modulesを削除して再インストール
rm -rf node_modules package-lock.json
npm install
```

### WebSocket接続エラー

- バックエンドが起動しているか確認
- ポート8000が正しいか確認
- CORS設定を確認

## ライセンス

このプロジェクトは研究用途のものです。
