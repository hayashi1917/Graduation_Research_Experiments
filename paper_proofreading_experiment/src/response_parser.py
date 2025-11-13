"""
LLM応答パーサー（Pydanticベース）
LLMの応答から修正点を抽出する
"""

import re
import json
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ProofreadingIssue(BaseModel):
    """校正指摘の1件を表すPydanticモデル"""

    issue_number: int = Field(..., description="指摘番号")
    before: str = Field(..., description="修正前の文", min_length=1)
    reasoning: str = Field(..., description="根拠", min_length=1)
    after: str = Field(..., description="修正後の文", min_length=1)

    @field_validator('before', 'after', 'reasoning')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """前後の空白を削除"""
        return v.strip()

    def __repr__(self):
        return (
            f"Issue {self.issue_number}:\n"
            f"  Before: {self.before[:50]}...\n"
            f"  Reasoning: {self.reasoning[:50]}...\n"
            f"  After: {self.after[:50]}..."
        )


class ProofreadingResponse(BaseModel):
    """校正応答全体を表すPydanticモデル"""

    issues: List[ProofreadingIssue] = Field(
        default_factory=list,
        description="指摘事項のリスト"
    )
    no_issues: bool = Field(
        default=False,
        description="指摘事項がないかどうか"
    )


class ResponseParser:
    """LLM応答をパースするクラス（Pydantic対応）"""

    def parse_proofreading_response(self, response: str) -> List[ProofreadingIssue]:
        """
        校正応答をパースして修正点のリストを返す

        Args:
            response: LLMの応答テキスト

        Returns:
            ProofreadingIssueのリスト
        """
        # 「指摘事項はありません」が含まれている場合は空リストを返す
        if "指摘事項はありません" in response:
            return []

        # まずJSON形式でのパースを試みる（最も信頼性が高い）
        issues = self._try_parse_json(response)
        if issues:
            return issues

        # JSON失敗時は正規表現によるパースを試みる
        issues = self._try_parse_with_regex(response)
        return issues

    def _try_parse_json(self, response: str) -> List[ProofreadingIssue]:
        """
        JSON形式でのパースを試みる

        LLMがJSON形式で応答した場合、それを優先的に使用する
        """
        # JSONブロックを抽出（```json ... ``` または { ... }）
        json_patterns = [
            r'```json\s*(\{.*?\}|\[.*?\])\s*```',
            r'```\s*(\{.*?\}|\[.*?\])\s*```',
            r'(\{[\s\S]*?"issues"[\s\S]*?\})',
            r'(\[[\s\S]*?\])',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)

                    # データがリストの場合
                    if isinstance(data, list):
                        issues = []
                        for i, item in enumerate(data, 1):
                            # issue_numberがない場合は追加
                            if 'issue_number' not in item:
                                item['issue_number'] = i
                            try:
                                issues.append(ProofreadingIssue(**item))
                            except Exception:
                                continue
                        if issues:
                            return issues

                    # データが辞書でissuesキーを持つ場合
                    elif isinstance(data, dict):
                        if 'issues' in data:
                            issues = []
                            for i, item in enumerate(data['issues'], 1):
                                if 'issue_number' not in item:
                                    item['issue_number'] = i
                                try:
                                    issues.append(ProofreadingIssue(**item))
                                except Exception:
                                    continue
                            if issues:
                                return issues
                        # 単一の指摘の場合
                        elif all(k in data for k in ['before', 'after', 'reasoning']):
                            if 'issue_number' not in data:
                                data['issue_number'] = 1
                            try:
                                return [ProofreadingIssue(**data)]
                            except Exception:
                                pass

                except (json.JSONDecodeError, Exception):
                    continue

        return []

    def _try_parse_with_regex(self, response: str) -> List[ProofreadingIssue]:
        """
        正規表現によるパース（フォールバック）

        複数のパターンを試して、最も多くマッチしたものを採用
        """
        issues = []

        # パターン1: 修正前の文、根拠、修正後の文（コードブロック付き、箇条書きマーカー付き）
        pattern1 = r'[*•\-]?\s*\*\*修正前の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```\s*[*•\-]?\s*\*\*根拠:\*\*\s*(.*?)\s*[*•\-]?\s*\*\*修正後の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```'
        issues = self._extract_issues_with_pattern(pattern1, response)
        if issues:
            return issues

        # パターン2: 箇条書きマーカーなし
        pattern2 = r'\*\*修正前の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```\s*\*\*根拠:\*\*\s*(.*?)\s*\*\*修正後の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```'
        issues = self._extract_issues_with_pattern(pattern2, response)
        if issues:
            return issues

        # パターン3: コードブロックなし
        pattern3 = r'(?:修正前|Before)[:：]\s*[`\n]*(.*?)[`\n]*\s*(?:根拠|理由|Reasoning)[:：]\s*(.*?)\s*(?:修正後|After)[:：]\s*[`\n]*(.*?)[`\n]*(?=\n\n|\Z)'
        issues = self._extract_issues_with_pattern(pattern3, response)
        if issues:
            return issues

        return []

    def _extract_issues_with_pattern(
        self,
        pattern: str,
        response: str
    ) -> List[ProofreadingIssue]:
        """
        指定されたパターンで指摘を抽出
        """
        matches = list(re.finditer(pattern, response, re.DOTALL | re.IGNORECASE))
        issues = []

        for i, match in enumerate(matches, 1):
            try:
                before = match.group(1).strip()
                reasoning = match.group(2).strip()
                after = match.group(3).strip()

                if before and after:
                    issue = ProofreadingIssue(
                        issue_number=i,
                        before=before,
                        reasoning=reasoning,
                        after=after,
                    )
                    issues.append(issue)
            except Exception:
                continue

        return issues

    def display_issues(self, issues: List[ProofreadingIssue]):
        """
        修正点を読みやすく表示する

        Args:
            issues: ProofreadingIssueのリスト
        """
        if not issues:
            print("指摘事項はありません。")
            return

        print(f"\n{'='*60}")
        print(f"検出された指摘: {len(issues)}件")
        print(f"{'='*60}\n")

        for issue in issues:
            print(f"【指摘 {issue.issue_number}】")
            print(f"\n修正前の文:")
            print(f"  {issue.before}")
            print(f"\n根拠:")
            print(f"  {issue.reasoning}")
            print(f"\n修正後の文:")
            print(f"  {issue.after}")
            print(f"\n{'-'*60}\n")


def test_parser():
    """パーサーのテスト"""
    parser = ResponseParser()

    # テスト1: Markdown形式の応答
    test_response_1 = """
以下の修正点があります。

**修正前の文:**
```
The data is analyzed using machine learning.
```
**根拠:** 主語が複数形の場合、動詞も複数形にすべきです。
**修正後の文:**
```
The data are analyzed using machine learning.
```

**修正前の文:**
```
We use a novel approach.
```
**根拠:** 冠詞が不適切です。
**修正後の文:**
```
We use the novel approach.
```
"""

    print("=== Test 1: Markdown形式 ===")
    issues = parser.parse_proofreading_response(test_response_1)
    parser.display_issues(issues)
    print(f"解析された指摘数: {len(issues)}\n")

    # テスト2: JSON形式の応答
    test_response_2 = """
```json
{
    "issues": [
        {
            "before": "The data is analyzed using machine learning.",
            "reasoning": "主語が複数形の場合、動詞も複数形にすべきです。",
            "after": "The data are analyzed using machine learning."
        },
        {
            "before": "We use a novel approach.",
            "reasoning": "冠詞が不適切です。",
            "after": "We use the novel approach."
        }
    ]
}
```
"""

    print("=== Test 2: JSON形式 ===")
    issues = parser.parse_proofreading_response(test_response_2)
    parser.display_issues(issues)
    print(f"解析された指摘数: {len(issues)}\n")

    # テスト3: 指摘なし
    test_response_3 = "指摘事項はありません。"

    print("=== Test 3: 指摘なし ===")
    issues = parser.parse_proofreading_response(test_response_3)
    parser.display_issues(issues)
    print(f"解析された指摘数: {len(issues)}\n")


if __name__ == "__main__":
    test_parser()
