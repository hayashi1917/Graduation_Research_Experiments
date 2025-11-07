#!/bin/bash
# 実験を順次実行するスクリプト

set -e  # エラーが発生したら即座に終了

# 使用方法を表示
if [ "$#" -ne 1 ]; then
    echo "使用方法: $0 <paper_id>"
    echo "例: $0 paper001"
    exit 1
fi

PAPER_ID=$1

echo "========================================"
echo "学術論文形式校正実験"
echo "論文ID: $PAPER_ID"
echo "========================================"
echo ""

# srcディレクトリに移動
cd src

# フェーズ1: クリーン化
echo "フェーズ1: クリーン化を開始..."
python main.py --paper-id "$PAPER_ID" --phase 1

echo ""
echo "フェーズ1が完了しました。"
echo "続行する前に、論文が適切にクリーン化されていることを確認してください。"
echo "Enter キーを押して次のフェーズに進んでください..."
read -r

# フェーズ2: 誤り埋め込み
echo ""
echo "フェーズ2: 誤り埋め込みを開始..."
python main.py --paper-id "$PAPER_ID" --phase 2

echo ""
echo "フェーズ2が完了しました。"
echo "埋め込まれた誤りを論文ファイル（TeXファイル）に手動で反映してください。"
echo "修正が完了したら Enter キーを押して次のフェーズに進んでください..."
read -r

# フェーズ3: 校正実験
echo ""
echo "フェーズ3: 校正実験を開始..."
python main.py --paper-id "$PAPER_ID" --phase 3

echo ""
echo "========================================"
echo "実験完了"
echo "論文ID: $PAPER_ID"
echo "========================================"
echo ""
echo "結果は data/results/ に保存されています。"
