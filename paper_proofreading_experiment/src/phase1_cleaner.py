"""
フェーズ1: クリーン化モジュール
論文をクリーンな状態にする（LLMが指摘事項なしと判断するまで反復）
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from llm_client import LLMClient
from data_manager import DataManager
from response_parser import ResponseParser, ProofreadingIssue
from paper_manager import PaperManager


class Phase1Cleaner:
    """論文のクリーン化を実行するクラス"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        paper_manager: PaperManager,
        prompt_template: str,
        checklist: str,
        max_iterations: int = 10,
    ):
        """
        Args:
            llm_client: LLMクライアント
            data_manager: データマネージャー
            paper_manager: 論文マネージャー
            prompt_template: プロンプトテンプレート
            checklist: チェックリスト
            max_iterations: 最大反復回数
        """
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.paper_manager = paper_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.max_iterations = max_iterations
        self.parser = ResponseParser()

    def run(
        self,
        paper_id: str,
        pdf_path: Path,
    ) -> Dict[str, Any]:
        """
        クリーン化を実行

        Args:
            paper_id: 論文ID
            pdf_path: PDFファイルのパス

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

            # 論文のバージョンを保存（イテレーション開始時）
            self.paper_manager.save_version(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                pdf_path=pdf_path,
            )

            # LLMを呼び出す
            print("LLMに校正を依頼中...")
            response = self.llm_client.call(
                prompt=prompt,
                pdf_path=pdf_path,
            )

            # プロンプトと応答を保存
            self.data_manager.save_prompt(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                prompt=prompt,
            )
            self.data_manager.save_response(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                response=response,
            )

            print(f"\n✓ LLMの応答を受信しました")

            # 応答をパースして指摘を抽出
            parse_result = self.parser.parse_proofreading_response(response)

            if parse_result.no_issues:
                print("✓ クリーン化完了（指摘事項なし）")
                stopped_reason = "no_issues"

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

            issues = parse_result.issues

            # 指摘が1つもない場合（パース失敗の可能性）
            if not issues:
                print("\n応答から指摘を抽出できませんでした。")
                print("生のLLM応答を確認してください:")
                print(f"\n{'-'*60}")
                print(response)
                print(f"{'-'*60}\n")

                cont = input("次のイテレーションに進みますか？ [Y/N]: ").strip().upper()
                if cont != "Y":
                    stopped_reason = "parse_failed"
                    break
                continue

            # 修正点がある場合はユーザーに確認
            print(f"\n修正点が検出されました: {len(issues)}件")
            self.parser.display_issues(issues)

            print("\n各指摘について判断してください:")
            print("  [A] 承認: 正しい指摘として記録")
            print("  [M] 手動: 手動で修正")
            print("  [S] スキップ: 誤検出として該当項目を除外")
            print("  [Q] 中断: クリーン化を中断")

            # インタラクティブな判断
            detected_in_iteration = []
            new_excluded = []

            for issue in issues:
                print(f"\n{'='*60}")
                print(f"【指摘 {issue.issue_number}/{len(issues)}】")
                print(f"\n修正前: {issue.before[:100]}...")
                print(f"根拠: {issue.reasoning[:100]}...")
                print(f"修正後: {issue.after[:100]}...")
                print(f"{'='*60}")

                action = input("\n[A]承認 / [M]手動 / [S]スキップ / [Q]中断: ").strip().upper()

                if action == "A":
                    print("→ 正しい指摘として記録します。必要に応じて後でPDFを更新してください。")
                    detected_in_iteration.append(f"issue_{issue.issue_number}_accepted")

                elif action == "M":
                    print("→ 手動で修正してください。")
                    print(f"\n修正前: {issue.before}")
                    print(f"修正後: {issue.after}")
                    input("\n修正完了後、Enter キーを押してください...")
                    detected_in_iteration.append(f"issue_{issue.issue_number}_manual")

                elif action == "S":
                    print("→ スキップします（誤検出として該当項目を除外）。")

                    # チェックリスト項目を入力
                    item = input("除外するチェックリスト項目名: ").strip()
                    reason = input("除外理由（短く）: ").strip()

                    if not item:
                        print("→ 項目名が入力されていません。もう一度入力してください。")
                        continue

                    if item in excluded_items:
                        print("→ その項目は既に除外済みです。別の項目を指定してください。")
                        continue

                    new_excluded.append(item)
                    excluded_items.append(item)

                    # 除外項目を記録
                    self.data_manager.record_excluded_item(
                        paper_id=paper_id,
                        checklist_item=item,
                        reason=reason,
                        example_case=f"phase1_iteration_{iteration}_issue{issue.issue_number}",
                    )

                elif action == "Q":
                    print("\nクリーン化を中断します。")
                    stopped_reason = "user_abort"
                    break

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
