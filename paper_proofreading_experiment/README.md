# 学術論文形式校正実験プログラム

LLMによる学術論文の形式的校正の可能性を検証する実験の半自動化プログラムです。

## 概要

このプログラムは、以下の3つのフェーズから構成される実験を半自動化します：

1. **フェーズ1: クリーン化** - 論文をLLMが「指摘事項なし」と判断する状態にする
2. **フェーズ2: 誤り埋め込み** - チェックリストに基づいて意図的な誤りを埋め込む
3. **フェーズ3: 校正実験** - 誤りを反復的に検出・修正し、検出率を測定

## プロジェクト構造

```
paper_proofreading_experiment/
├── config/
│   ├── prompts.yaml          # プロンプトテンプレート
│   ├── checklist.md          # チェックリスト
│   └── settings.yaml         # 実験設定
├── data/
│   ├── papers/               # 論文データ（PDF + TeX）
│   │   ├── paper001/
│   │   │   ├── paper001.pdf
│   │   │   └── paper001.tex
│   │   └── paper002/
│   │       ├── paper002.pdf
│   │       └── paper002.tex
│   ├── results/              # 実験結果（CSV）
│   │   ├── embedded_errors.csv
│   │   ├── iteration_log.csv
│   │   ├── excluded_items.csv
│   │   └── summary.csv
│   ├── logs/                 # LLM応答・プロンプトログ
│   │   └── paper001/
│   │       ├── phase1_iteration_1_prompt.txt
│   │       ├── phase1_iteration_1_response.txt
│   │       ├── phase2_iteration_1_response.txt
│   │       └── phase3_iteration_1_response.txt
│   └── versions/             # 論文のバージョン履歴
│       └── paper001/
│           ├── phase1_iter1_20250107_120000/
│           │   ├── paper001.pdf
│           │   └── paper001.tex
│           └── phase3_iter1_20250107_130000/
│               ├── paper001.pdf
│               └── paper001.tex
├── src/
│   ├── llm_client.py         # LLM API呼び出し
│   ├── response_parser.py    # LLM応答のパース
│   ├── paper_manager.py      # 論文のバージョン管理・編集
│   ├── data_manager.py       # データ記録・管理
│   ├── phase1_cleaner.py     # フェーズ1: クリーン化
│   ├── phase2_embedder.py    # フェーズ2: 誤り埋め込み
│   ├── phase3_proofreader.py # フェーズ3: 校正実験
│   └── main.py               # メインプログラム
├── requirements.txt
└── README.md
```

## セットアップ

### 1. 仮想環境の作成（推奨）

macOSやHomebrew Python環境では、システムのPython環境を保護するため、仮想環境の使用が推奨されます。

```bash
# プロジェクトディレクトリに移動
cd paper_proofreading_experiment

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 仮想環境が有効化されると、プロンプトに (venv) が表示されます
```

**注意**: 仮想環境を使用しない場合、macOSでは以下のエラーが発生することがあります：
```
error: externally-managed-environment
```

### 2. 依存パッケージのインストール

仮想環境を有効化した状態で、依存パッケージをインストールします：

```bash
pip install -r requirements.txt
```

### 3. APIキーの設定

環境変数としてAPIキーを設定してください：

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

または、`.env`ファイルに記載：

```
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 4. 論文ファイルの配置

`data/papers/` 配下に論文IDごとのディレクトリを作成し、PDFとTeXファイルを配置してください：

```
data/papers/
├── paper001/
│   ├── paper001.pdf
│   └── paper001.tex
├── paper002/
│   ├── paper002.pdf
│   └── paper002.tex
...
```

### 5. チェックリストの準備

`config/checklist.md` に実験で使用するチェックリストを記載してください。

サンプルが既に用意されていますが、実験では「後藤版 英語論文自己チェックリスト」など、実際のチェックリストに置き換えてください。

## 使用方法

**重要**: プログラムを実行する前に、必ず仮想環境を有効化してください。

```bash
# プロジェクトディレクトリに移動
cd paper_proofreading_experiment

# 仮想環境を有効化（毎回必要）
source venv/bin/activate
```

### フェーズ1: クリーン化

論文をクリーンな状態にします（LLMが「指摘事項なし」と判断するまで反復）。

```bash
cd src
python main.py --paper-id paper001 --phase 1
```

**プロセス:**
1. 各イテレーションの開始時に論文のバージョンを自動保存
2. LLMに校正を依頼（プロンプトと応答を自動記録）
3. LLMの応答から指摘を自動抽出・表示
4. 各指摘について判断:
   - **[A] 自動適用**: 正しい指摘なので自動的にTeXファイルに反映
   - **[M] 手動**: 手動で修正
   - **[S] スキップ**: 誤検出
   - **[D] 判断困難**: 内容理解が必要（該当項目を除外）
   - **[Q] 中断**: クリーン化を中断
5. 「指摘事項はありません」が出るまで繰り返す

**重要:**
- 判断困難として除外した項目は、フェーズ2以降でもチェック対象から除外されます
- 各イテレーションの論文ファイルは `data/versions/` に保存されます
- プロンプトと応答は `data/logs/` に保存されます

### フェーズ2: 誤り埋め込み

チェックリストに基づいて意図的な誤りを埋め込みます。

```bash
cd src
python main.py --paper-id paper001 --phase 2
```

**プロセス:**
1. LLMに誤り埋め込みを依頼（10件）
2. 埋め込まれた誤りのリストを確認
3. 手動で論文（TeXファイル）に誤りを反映

**重要:** フェーズ2の後、必ず手動で論文ファイルを更新してください。

### フェーズ3: 校正実験

誤りが埋め込まれた論文を反復的に校正します。

```bash
cd src
python main.py --paper-id paper001 --phase 3
```

**プロセス:**
1. 各イテレーションの開始時に論文のバージョンを自動保存
2. LLMに校正を依頼（プロンプトと応答を自動記録）
3. LLMの応答から指摘を自動抽出・表示
4. 各指摘について判断:
   - **[A] 自動適用**: 正しい指摘なので自動的にTeXファイルに反映
   - **[M] 手動**: 手動で修正
   - **[S] スキップ**: 誤検出
   - **[D] 判断困難**: 内容理解が必要（該当項目を除外）
   - **[Q] 中断**: 校正を中断
5. 「指摘事項はありません」が出るまで繰り返す（最大10回）

**重要:**
- 各イテレーションの論文ファイルは `data/versions/` に保存されます
- プロンプトと応答は `data/logs/` に保存されます
- 検出された誤りは自動的に記録され、検出率が計算されます

## 実験データの記録

実験データは自動的に `data/results/` に記録されます：

### 1. embedded_errors.csv

埋め込まれた誤りのリスト

| カラム | 説明 |
|--------|------|
| paper_id | 論文ID |
| error_id | 誤りID |
| checklist_item | チェックリスト項目 |
| category | カテゴリ |
| before | 修正前の文 |
| after | 修正後の文（誤りを含む） |
| location | 該当箇所 |
| timestamp | タイムスタンプ |

### 2. iteration_log.csv

各イテレーションのログ

| カラム | 説明 |
|--------|------|
| paper_id | 論文ID |
| phase | フェーズ |
| iteration | イテレーション番号 |
| timestamp | タイムスタンプ |
| llm_model | 使用したLLMモデル |
| detected_errors | 検出された誤りのリスト（JSON） |
| new_issues_count | 新規検出数 |
| excluded_items | 除外項目リスト（JSON） |
| stopped_reason | 停止理由 |

### 3. excluded_items.csv

除外されたチェックリスト項目

| カラム | 説明 |
|--------|------|
| paper_id | 論文ID |
| checklist_item | チェックリスト項目 |
| reason | 除外理由 |
| timestamp | タイムスタンプ |
| example_case | 具体例 |

### 4. summary.csv

実験のサマリー

| カラム | 説明 |
|--------|------|
| paper_id | 論文ID |
| total_embedded | 埋め込んだ誤り総数 |
| total_detected | 検出された誤り総数 |
| detection_rate | 検出率（%） |
| phase1_iterations | フェーズ1の反復回数 |
| phase3_iterations | フェーズ3の反復回数 |
| excluded_items_count | 除外項目数 |
| completion_time | 完了時間 |

## 設定のカスタマイズ

### config/settings.yaml

実験パラメータやLLM設定を変更できます：

```yaml
llm:
  proofreading:
    provider: "gemini"
    model: "gemini-1.5-pro"
    temperature: 0.0
    api_key_env: "GEMINI_API_KEY"

  embedding:
    provider: "claude"
    model: "claude-3-5-sonnet-20241022"
    temperature: 0.0
    api_key_env: "ANTHROPIC_API_KEY"

experiment:
  num_errors: 10              # 埋め込む誤りの数
  max_errors_per_item: 2      # 同一項目からの最大選出数
  max_iterations: 10          # 最大反復回数
  num_papers: 10              # 論文の総数
```

### config/prompts.yaml

プロンプトテンプレートをカスタマイズできます。

### config/checklist.md

実験で使用するチェックリストを記載してください。

## トラブルシューティング

### パッケージインストールエラー（macOS）

```
error: externally-managed-environment
```

→ 仮想環境を使用してください（上記「仮想環境の作成」参照）

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### APIキーエラー

```
ValueError: 環境変数 GEMINI_API_KEY が設定されていません。
```

→ 環境変数を設定してください（上記「APIキーの設定」参照）

### 論文ファイルが見つからない

```
エラー: 論文ファイルが見つかりません。
```

→ `data/papers/{paper_id}/` ディレクトリに論文ファイルを配置してください

### LLMの応答が期待通りでない

- プロンプトを確認・調整してください（`config/prompts.yaml`）
- LLMのtemperatureを調整してください（`config/settings.yaml`）

## 注意事項

1. **手動操作が必要な箇所**
   - フェーズ1: LLMの指摘に基づく論文の修正
   - フェーズ2: 埋め込まれた誤りを論文に反映
   - フェーズ3: 各指摘の判断と修正

2. **データのバックアップ**
   - 実験前に論文ファイルのバックアップを取ることを推奨します

3. **API利用料金**
   - LLM APIの利用には料金が発生します
   - 大量の論文を処理する場合は特に注意してください

## ライセンス

このプログラムは卒業研究の一環として作成されました。

## 問い合わせ

不明な点があれば、開発者に問い合わせてください。
