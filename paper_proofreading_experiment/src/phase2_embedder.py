"""
フェーズ2: 誤り埋め込みモジュール（Pydanticベース）
意図的な誤りをチェックリストに基づいて論文に埋め込む
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import ValidationError

from llm_client import LLMClient
from data_manager import DataManager
from embedded_error_models import EmbeddedError, EmbeddingResponse


class Phase2Embedder:
    """誤りの埋め込みを実行するクラス"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        prompt_template: str,
        checklist: str,
        num_errors: int = 10,
        excluded_items: List[str] = None,
    ):
        """
        Args:
            llm_client: LLMクライアント（Claudeを推奨）
            data_manager: データマネージャー
            prompt_template: プロンプトテンプレート
            checklist: チェックリスト
            num_errors: 埋め込む誤りの数
            excluded_items: 除外するチェックリスト項目
        """
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.num_errors = num_errors
        self.excluded_items = excluded_items or []

    def run(
        self,
        paper_id: str,
        pdf_path: Path,
    ) -> Dict[str, Any]:
        """
        誤り埋め込みを実行

        Args:
            paper_id: 論文ID
            pdf_path: PDFファイルのパス

        Returns:
            埋め込まれた誤りのリスト
        """
        print(f"\n{'='*60}")
        print(f"フェーズ2: 誤り埋め込みを開始 - {paper_id}")
        print(f"{'='*60}\n")

        # 除外項目のリストを文字列に変換
        excluded_items_str = "\n".join(
            [f"- {item}" for item in self.excluded_items]
        ) if self.excluded_items else "なし"

        # プロンプトを構築
        prompt = self.prompt_template.format(
            excluded_items=excluded_items_str,
            checklist=self.checklist,
        )

        # LLMを呼び出す
        print("LLMに誤り埋め込みを依頼中...")
        response = self.llm_client.call(
            prompt=prompt,
            pdf_path=pdf_path,
        )

        # 応答を保存
        self.data_manager.save_response(
            paper_id=paper_id,
            phase="phase2",
            iteration=1,
            response=response,
        )

        print(f"\nLLMの応答:\n{'-'*40}")
        print(response)
        print(f"{'-'*40}\n")

        # JSONを抽出してパース
        errors = self._parse_errors_from_response(response)

        if not errors:
            print("⚠ 誤りの抽出に失敗しました。")
            print("応答を確認して、手動で誤りを記録してください。")
            return {"errors": [], "success": False}

        # 誤りをデータベースに記録
        print(f"\n{len(errors)}件の誤りを記録します:\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error.get('checklist_item', 'N/A')} - {error.get('category', 'N/A')}")
            print(f"   場所: {error.get('location', 'N/A')}")
            print(f"   説明: {error.get('description', 'N/A')}\n")

            # CSVに記録
            self.data_manager.record_embedded_error(
                paper_id=paper_id,
                error_id=error.get("error_id", i),
                checklist_item=error.get("checklist_item", ""),
                category=error.get("category", ""),
                before=error.get("before", ""),
                after=error.get("after", ""),
                location=error.get("location", ""),
            )

        print("✓ 誤りの記録完了")

        # ユーザーに確認
        print("\n次のステップ:")
        print("1. 上記の誤りを実際の論文（PDFファイル）に反映してください")
        print("2. 修正が完了したら、フェーズ3（校正実験）に進んでください")

        print(f"\n{'='*60}")
        print(f"フェーズ2完了")
        print(f"埋め込まれた誤り数: {len(errors)}")
        print(f"{'='*60}\n")

        return {
            "errors": errors,
            "success": True,
            "count": len(errors),
        }

    def _parse_errors_from_response(self, response: str) -> List[Dict[str, Any]]:
        """
        LLMの応答からJSON形式の誤りリストを抽出（Pydanticベース）

        Args:
            response: LLMの応答テキスト

        Returns:
            誤りのリスト（辞書形式）
        """
        # まずPydanticモデルでパースを試みる
        errors = self._try_parse_with_pydantic(response)
        if errors:
            # Pydanticモデルを辞書に変換して返す
            return [error.model_dump() for error in errors]

        # Pydantic失敗時はレガシーのJSONパースを試みる
        return self._try_parse_json_legacy(response)

    def _try_parse_with_pydantic(self, response: str) -> List[EmbeddedError]:
        """
        Pydanticモデルを使ってパース

        Args:
            response: LLMの応答テキスト

        Returns:
            EmbeddedErrorのリスト
        """
        # JSONブロックを抽出（```json ... ``` または { ... } を探す）
        json_patterns = [
            r"```json\s*(\{.*?\}|\[.*?\])\s*```",
            r"```\s*(\{.*?\}|\[.*?\])\s*```",
            r"(\{[\s\S]*\"errors\"[\s\S]*?\})",
            r"(\[[\s\S]*?\])",
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)

                    # データがリストの場合
                    if isinstance(data, list):
                        errors = []
                        for i, item in enumerate(data, 1):
                            if 'error_id' not in item:
                                item['error_id'] = i
                            try:
                                errors.append(EmbeddedError(**item))
                            except ValidationError:
                                continue
                        if errors:
                            return errors

                    # データが辞書でerrorsキーを持つ場合
                    elif isinstance(data, dict):
                        if 'errors' in data:
                            errors = []
                            for i, item in enumerate(data['errors'], 1):
                                if 'error_id' not in item:
                                    item['error_id'] = i
                                try:
                                    errors.append(EmbeddedError(**item))
                                except ValidationError:
                                    continue
                            if errors:
                                return errors

                except (json.JSONDecodeError, ValidationError):
                    continue

        return []

    def _try_parse_json_legacy(self, response: str) -> List[Dict[str, Any]]:
        """
        レガシーのJSONパース（フォールバック）

        Args:
            response: LLMの応答テキスト

        Returns:
            誤りのリスト（辞書形式）
        """
        # JSONブロックを抽出（```json ... ``` または { ... } を探す）
        json_patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"```\s*(\{.*?\})\s*```",
            r"(\{[\s\S]*\"errors\"[\s\S]*?\})",
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    if "errors" in data:
                        return data["errors"]
                except json.JSONDecodeError:
                    continue

        # JSON抽出に失敗した場合は空のリストを返す
        return []


if __name__ == "__main__":
    print("Phase2 Embedderモジュールのテスト")
    print("注意: このモジュールは単体では実行できません。")
    print("main.pyから実行してください。")
