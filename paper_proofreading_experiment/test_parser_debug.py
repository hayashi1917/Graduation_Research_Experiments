#!/usr/bin/env python3
"""
レスポンスパーサーのデバッグスクリプト
実際のGemini 2.5 Proの応答形式をテストする
"""

import re
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from response_parser import ResponseParser

# 実際のGemini 2.5 Proの応答例（ユーザーが遭遇した形式）
test_response = """以下の指摘事項があります。

* **修正前の文:**
```
This is a sample text that needs correction.
```
* **根拠:** 文法的な誤りがあります。
* **修正後の文:**
```
This is sample text that needs correction.
```

* **修正前の文:**
```
The data is analyzed using machine learning.
```
* **根拠:** 主語が複数形の場合、動詞も複数形にすべきです。
* **修正後の文:**
```
The data are analyzed using machine learning.
```

* **修正前の文:**
```
We propose a novel
approach for this problem.
```
* **根拠:** 改行が不適切です。
* **修正後の文:**
```
We propose a novel approach for this problem.
```
"""

# パーサーをテスト
parser = ResponseParser()

print("="*70)
print("レスポンスパーサーのデバッグ")
print("="*70)

print("\nテスト対象の応答:")
print("-"*70)
print(test_response)
print("-"*70)

# 現在のパターンを表示
pattern1 = r'[*•\-]?\s*\*\*修正前の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```\s*[*•\-]?\s*\*\*根拠:\*\*\s*(.*?)\s*[*•\-]?\s*\*\*修正後の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```'

print("\n使用中のパターン1:")
print(pattern1)

# パターン1でマッチを試す
matches = list(re.finditer(pattern1, test_response, re.DOTALL))
print(f"\nパターン1のマッチ数: {len(matches)}")

if matches:
    for i, match in enumerate(matches, 1):
        print(f"\nマッチ {i}:")
        print(f"  修正前: {match.group(1)[:50]}...")
        print(f"  根拠: {match.group(2)[:50]}...")
        print(f"  修正後: {match.group(3)[:50]}...")
else:
    print("  マッチなし")

# 実際のパース処理を実行
print("\n" + "="*70)
print("ResponseParser.parse_proofreading_response() の結果:")
print("="*70)

issues = parser.parse_proofreading_response(test_response)

print(f"\n抽出された指摘数: {len(issues)}")

if issues:
    parser.display_issues(issues)
else:
    print("指摘が抽出されませんでした。")

# より詳細なデバッグ: 応答を行ごとに表示
print("\n" + "="*70)
print("応答の詳細分析（各行の内容）:")
print("="*70)

lines = test_response.split('\n')
for i, line in enumerate(lines, 1):
    print(f"{i:3d}: {repr(line)}")
