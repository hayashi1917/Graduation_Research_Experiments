"""
フェーズ1: クリーン化モジュール
論文をクリーンな状態にする（LLMが指摘事項なしと判断するまで反復）
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from llm_client import LLMClient
from data_manager import DataManager


class Phase1Cleaner:
    """論文のクリーン化を実行するクラス"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        prompt_template: str,
        checklist: str,
        max_iterations: int = 10,
    ):
        """
        Args:
            llm_client: LLMクライアント
            data_manager: データマネージャー
            prompt_template: プロンプトテンプレート
            checklist: チェックリスト
            max_iterations: 最大反復回数
        """
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.max_iterations = max_iterations

    def run(
        self,
        paper_id: str,
        pdf_path: Path,
        tex_path: Path,
    ) -> Dict[str, Any]:
        """
        クリーン化を実行

        Args:
            paper_id: 論文ID
            pdf_path: PDFファイルのパス
            tex_path: TeXファイルのパス

        Returns:
            実行結果（反復回数、停止理由など）
        """
        print(f"\n{'='*60}")
        print(f"フェーズ1: クリーン化を開始 - {paper_id}")
        print(f"{'='*60}\n")

        iteration = 0
        stopped_reason = ""

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- イテレーション {iteration} ---")

            # プロンプトを構築
            prompt = self.prompt_template.format(
                excluded_items="なし",
                checklist=self.checklist,
            )

            # LLMを呼び出す
            print("LLMに校正を依頼中...")
            response = self.llm_client.call(
                prompt=prompt,
                pdf_path=pdf_path,
                tex_path=tex_path,
            )

            # 応答を保存
            self.data_manager.save_response(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                response=response,
            )

            print(f"\nLLMの応答:\n{'-'*40}")
            print(response)
            print(f"{'-'*40}\n")

            # 「指摘事項はありません」が含まれているか確認
            if "指摘事項はありません" in response:
                print("✓ クリーン化完了（指摘事項なし）")
                stopped_reason = "no_issues"

                # イテレーションログを記録
                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=[],
                    stopped_reason=stopped_reason,
                )
                break

            # 修正点がある場合はユーザーに確認
            print("\n修正点が検出されました。")
            print("次のアクションを選択してください:")
            print("  1. 修正を適用して次のイテレーションへ")
            print("  2. 手動で修正（プログラムを一時停止）")
            print("  3. クリーン化を中断")

            choice = input("\n選択 (1/2/3): ").strip()

            if choice == "1":
                print("\n手動で論文を修正してください。")
                print("修正が完了したら Enter キーを押してください...")
                input()

                # イテレーションログを記録
                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=["manual_review"],
                    new_issues_count=1,
                    excluded_items=[],
                    stopped_reason="",
                )

            elif choice == "2":
                print("\nプログラムを一時停止します。")
                print("論文を修正後、再度実行してください。")
                stopped_reason = "manual_pause"

                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=["manual_review"],
                    new_issues_count=1,
                    excluded_items=[],
                    stopped_reason=stopped_reason,
                )
                break

            elif choice == "3":
                print("\nクリーン化を中断します。")
                stopped_reason = "user_abort"

                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=["manual_review"],
                    new_issues_count=1,
                    excluded_items=[],
                    stopped_reason=stopped_reason,
                )
                break

        # 最大反復回数に到達した場合
        if iteration >= self.max_iterations and stopped_reason == "":
            print(f"\n最大反復回数（{self.max_iterations}）に到達しました。")
            stopped_reason = "max_iterations"

        print(f"\n{'='*60}")
        print(f"フェーズ1完了")
        print(f"総イテレーション数: {iteration}")
        print(f"停止理由: {stopped_reason}")
        print(f"{'='*60}\n")

        return {
            "iterations": iteration,
            "stopped_reason": stopped_reason,
        }


if __name__ == "__main__":
    print("Phase1 Cleanerモジュールのテスト")
    print("注意: このモジュールは単体では実行できません。")
    print("main.pyから実行してください。")
