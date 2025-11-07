"""
LLM応答パーサー
LLMの応答から修正点を抽出する
"""

import re
from typing import List, Dict, Any, Optional


class ProofreadingIssue:
    """校正指摘の1件を表すクラス"""

    def __init__(
        self,
        issue_number: int,
        before: str,
        reasoning: str,
        after: str,
    ):
        self.issue_number = issue_number
        self.before = before
        self.reasoning = reasoning
        self.after = after

    def __repr__(self):
        return (
            f"Issue {self.issue_number}:\n"
            f"  Before: {self.before[:50]}...\n"
            f"  Reasoning: {self.reasoning[:50]}...\n"
            f"  After: {self.after[:50]}..."
        )


class ResponseParser:
    """LLM応答をパースするクラス"""

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

        issues = []

        # パターン1: 修正前の文、根拠、修正後の文の順（箇条書きマーカー付き）
        # * **修正前の文:**
        # ```
        # ...
        # ```
        # * **根拠:** ...
        # * **修正後の文:**
        # ```
        # ...
        # ```

        # より柔軟なパターン: 箇条書きマーカー、コードブロック内の改行を考慮
        # \s*```(?:\w+)?\s* で言語指定あり/なし両方に対応
        # (.*?) で改行を含むコンテンツをキャプチャ（DOTALL モードで . が \n にマッチ）
        pattern1 = r'[*•\-]?\s*\*\*修正前の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```\s*[*•\-]?\s*\*\*根拠:\*\*\s*(.*?)\s*[*•\-]?\s*\*\*修正後の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```'

        matches = list(re.finditer(pattern1, response, re.DOTALL))

        issue_number = 1
        for match in matches:
            before = match.group(1).strip()
            reasoning = match.group(2).strip()
            after = match.group(3).strip()

            if before and after:
                issues.append(ProofreadingIssue(
                    issue_number=issue_number,
                    before=before,
                    reasoning=reasoning,
                    after=after,
                ))
                issue_number += 1

        # パターン2: 箇条書きマーカーなし
        if not issues:
            pattern2 = r'\*\*修正前の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```\s*\*\*根拠:\*\*\s*(.*?)\s*\*\*修正後の文:\*\*\s*```(?:\w+)?\s*(.*?)\s*```'

            matches = list(re.finditer(pattern2, response, re.DOTALL))

            issue_number = 1
            for match in matches:
                before = match.group(1).strip()
                reasoning = match.group(2).strip()
                after = match.group(3).strip()

                if before and after:
                    issues.append(ProofreadingIssue(
                        issue_number=issue_number,
                        before=before,
                        reasoning=reasoning,
                        after=after,
                    ))
                    issue_number += 1

        # パターン3: より柔軟なパターン（コードブロックなし）
        if not issues:
            pattern3 = r'(?:修正前|Before)[:：]\s*[`\n]*(.*?)[`\n]*\s*(?:根拠|理由|Reasoning)[:：]\s*(.*?)\s*(?:修正後|After)[:：]\s*[`\n]*(.*?)[`\n]*(?=\n\n|\Z)'

            matches = list(re.finditer(pattern3, response, re.DOTALL | re.IGNORECASE))

            issue_number = 1
            for match in matches:
                before = match.group(1).strip()
                reasoning = match.group(2).strip()
                after = match.group(3).strip()

                if before and after:
                    issues.append(ProofreadingIssue(
                        issue_number=issue_number,
                        before=before,
                        reasoning=reasoning,
                        after=after,
                    ))
                    issue_number += 1

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

    # テスト用の応答
    test_response = """
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

    issues = parser.parse_proofreading_response(test_response)
    parser.display_issues(issues)

    print(f"\n解析された指摘数: {len(issues)}")


if __name__ == "__main__":
    test_parser()
