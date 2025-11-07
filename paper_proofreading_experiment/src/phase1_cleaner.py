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

        # 除外項目リストを初期化（既存の除外項目を取得）
        excluded_items = self.data_manager.get_excluded_items(paper_id)

        iteration = 0
        stopped_reason = ""

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- イテレーション {iteration} ---")

            # 除外項目リストを文字列に変換
            excluded_items_str = "\n".join(
                [f"- {item}" for item in excluded_items]
            ) if excluded_items else "なし"

            # プロンプトを構築
            prompt = self.prompt_template.format(
                excluded_items=excluded_items_str,
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
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )
                break

            # 修正点がある場合はユーザーに確認
            print("\n修正点が検出されました。")
            print("各指摘について判断してください:")
            print("  [A] 適用: 正しい指摘なので反映")
            print("  [S] スキップ: 誤検出")
            print("  [D] 判断困難: 内容理解が必要（該当項目を除外）")
            print("  [Q] 中断: クリーン化を中断")

            # インタラクティブな判断
            detected_in_iteration = []
            new_excluded = []

            while True:
                print("\n指摘を1つずつ処理します。")
                print("指摘番号を入力してください（例: 1）")
                print("すべて処理した場合は 'done' と入力してください。")

                choice = input("\n選択: ").strip().lower()

                if choice == "done":
                    break
                elif choice == "q":
                    print("\nクリーン化を中断します。")
                    stopped_reason = "user_abort"
                    break

                # 判断を取得
                print("\nこの指摘について:")
                action = input("[A]適用 / [S]スキップ / [D]判断困難: ").strip().upper()

                if action == "A":
                    print("→ 適用として記録します。")
                    detected_in_iteration.append(f"issue_{choice}")

                    # 実際に論文を修正
                    print("\n手動で論文を修正してください。")
                    print("修正が完了したら Enter キーを押してください...")
                    input()

                elif action == "S":
                    print("→ スキップします（誤検出として記録）。")

                elif action == "D":
                    print("→ 判断困難として記録し、該当項目を除外します。")

                    # チェックリスト項目を入力
                    item = input("除外するチェックリスト項目名: ").strip()
                    reason = input("除外理由（短く）: ").strip()

                    new_excluded.append(item)
                    excluded_items.append(item)

                    # 除外項目を記録
                    self.data_manager.record_excluded_item(
                        paper_id=paper_id,
                        checklist_item=item,
                        reason=reason,
                        example_case=f"phase1_iteration_{iteration}",
                    )

            # 中断判定
            if stopped_reason == "user_abort":
                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=detected_in_iteration,
                    new_issues_count=len(detected_in_iteration),
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )
                break

            # イテレーションログを記録
            self.data_manager.record_iteration(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                llm_model=self.llm_client.model,
                detected_errors=detected_in_iteration,
                new_issues_count=len(detected_in_iteration),
                excluded_items=excluded_items,
                stopped_reason="",
            )

            # 次のイテレーションに進むか確認
            print("\n次のイテレーションに進みますか？")
            cont = input("[Y] 続行 / [N] 終了: ").strip().upper()
            if cont != "Y":
                print("\nクリーン化を終了します。")
                stopped_reason = "user_stop"
                break

        # 最大反復回数に到達した場合
        if iteration >= self.max_iterations and stopped_reason == "":
            print(f"\n最大反復回数（{self.max_iterations}）に到達しました。")
            stopped_reason = "max_iterations"

        print(f"\n{'='*60}")
        print(f"フェーズ1完了")
        print(f"総イテレーション数: {iteration}")
        print(f"除外された項目数: {len(excluded_items)}")
        print(f"停止理由: {stopped_reason}")
        print(f"{'='*60}\n")

        return {
            "iterations": iteration,
            "excluded_items_count": len(excluded_items),
            "stopped_reason": stopped_reason,
        }


if __name__ == "__main__":
    print("Phase1 Cleanerモジュールのテスト")
    print("注意: このモジュールは単体では実行できません。")
    print("main.pyから実行してください。")
