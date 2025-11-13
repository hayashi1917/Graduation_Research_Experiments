"""
LLM応答パーサー（Pydanticベース）
LLMの応答から修正点を抽出する
"""

import ast
import re
import json
from typing import Any, List, Optional
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


class ProofreadingParseResult(BaseModel):
    """パース結果を保持するモデル"""

    issues: List[ProofreadingIssue] = Field(
        default_factory=list,
        description="抽出された指摘事項"
    )
    no_issues: bool = Field(
        default=False,
        description="LLM応答が指摘なしと判断されたか"
    )


class ResponseParser:
    """LLM応答をパースするクラス（Pydantic対応）"""

    def parse_proofreading_response(self, response: str) -> ProofreadingParseResult:
        """
        校正応答をパースして修正点のリストを返す

        Args:
            response: LLMの応答テキスト

        Returns:
            ProofreadingParseResult
        """
        # まずJSON形式でのパースを試みる（最も信頼性が高い）
        json_result = self._try_parse_json(response)
        if json_result is not None:  # Noneの場合のみフォールバック
            return json_result

        # JSON失敗時は正規表現によるパースを試みる（レガシー互換性のため）
        issues = self._try_parse_with_regex(response)
        if issues:
            return ProofreadingParseResult(issues=issues, no_issues=False)

        return ProofreadingParseResult(
            issues=[],
            no_issues=self._detect_no_issue_phrase(response)
        )

    def _try_parse_json(self, response: str) -> Optional[ProofreadingParseResult]:
        """
        JSON形式でのパースを試みる

        LLMがJSON形式で応答した場合、それを優先的に使用する

        Returns:
            ProofreadingParseResult、またはパース失敗時はNone
        """
        # JSONブロックを抽出（```json ... ``` または { ... }）
        json_patterns = [
            r'```json\s*(\{.*?\}|\[.*?\])\s*```',
            r'```\s*(\{.*?\}|\[.*?\])\s*```',
            r'(\{[\s\S]*?"issues"[\s\S]*?\})',
            r'(\{[\s\S]*?"no_issues"[\s\S]*?\})',
            r'(\[[\s\S]*?\])',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = self._loads_json_lenient(json_str)
                if data is None:
                    continue

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
                    return ProofreadingParseResult(
                        issues=issues,
                        no_issues=len(issues) == 0,
                    )

                # データが辞書の場合
                elif isinstance(data, dict):
                    # Pydanticモデルを使ってパース
                    try:
                        # no_issuesフラグがある場合
                        if 'no_issues' in data:
                            if data['no_issues'] is True:
                                # 修正点なし
                                return ProofreadingParseResult(issues=[], no_issues=True)
                            # no_issues: false の場合、issuesを処理
                            elif 'issues' in data:
                                issues = []
                                for i, item in enumerate(data['issues'], 1):
                                    if 'issue_number' not in item:
                                        item['issue_number'] = i
                                    try:
                                        issues.append(ProofreadingIssue(**item))
                                    except Exception:
                                        continue
                                return ProofreadingParseResult(
                                    issues=issues,
                                    no_issues=False,
                                )

                        # issuesキーがある場合（no_issuesフィールドなし）
                        elif 'issues' in data:
                            issues = []
                            for i, item in enumerate(data['issues'], 1):
                                if 'issue_number' not in item:
                                    item['issue_number'] = i
                                try:
                                    issues.append(ProofreadingIssue(**item))
                                except Exception:
                                    continue
                            return ProofreadingParseResult(
                                issues=issues,
                                no_issues=len(issues) == 0,
                            )

                        # 単一の指摘の場合
                        elif all(k in data for k in ['before', 'after', 'reasoning']):
                            if 'issue_number' not in data:
                                data['issue_number'] = 1
                            try:
                                return ProofreadingParseResult(
                                    issues=[ProofreadingIssue(**data)],
                                    no_issues=False,
                                )
                            except Exception:
                                pass

                    except Exception:
                        continue

        return None  # パース失敗

    def _loads_json_lenient(self, json_candidate: str) -> Optional[Any]:
        """多少フォーマットが崩れたJSONライクな文字列を解析"""

        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

        # JSONとしては不正でも、Pythonリテラルとして解釈できる場合がある
        sanitized = self._sanitize_json_like(json_candidate)

        try:
            return ast.literal_eval(sanitized)
        except Exception:
            return None

    def _sanitize_json_like(self, text: str) -> str:
        """literal_evalが扱えるように最低限のトークンを正規化"""

        replacements = {
            r'(?<!["\'])\btrue\b(?!["\'])': 'True',
            r'(?<!["\'])\bfalse\b(?!["\'])': 'False',
            r'(?<!["\'])\bnull\b(?!["\'])': 'None',
        }

        sanitized = text
        for pattern, replacement in replacements.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def _detect_no_issue_phrase(self, response: str) -> bool:
        """テキストから指摘なしのメッセージを検出"""
        normalized = response.lower()
        phrases = [
            "指摘事項はありません",
            "指摘はありません",
            "問題は検出されません",
            "no issues",
            "no issue",
            '"no_issues"\s*:\s*true',
        ]

        return any(re.search(phrase, normalized) for phrase in phrases)

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
    result = parser.parse_proofreading_response(test_response_1)
    parser.display_issues(result.issues)
    print(f"解析された指摘数: {len(result.issues)}\n")

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
    result = parser.parse_proofreading_response(test_response_2)
    parser.display_issues(result.issues)
    print(f"解析された指摘数: {len(result.issues)}\n")

    # テスト3: 指摘なし
    test_response_3 = "指摘事項はありません。"

    print("=== Test 3: 指摘なし ===")
    result = parser.parse_proofreading_response(test_response_3)
    parser.display_issues(result.issues)
    print(f"解析された指摘数: {len(result.issues)} / 指摘なし: {result.no_issues}\n")


if __name__ == "__main__":
    test_parser()
