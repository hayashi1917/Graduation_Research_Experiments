"""
WebSocket対応のPhaseアダプタークラス
既存のCLI版Phaseクラスをラップして、WebSocket経由で実行できるようにする
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import WebSocket

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_client import LLMClient
from data_manager import DataManager
from response_parser import ResponseParser, ProofreadingIssue
from paper_manager import PaperManager


class WebSocketPhase1Adapter:
    """フェーズ1のWebSocketアダプター"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        paper_manager: PaperManager,
        prompt_template: str,
        checklist: str,
        max_iterations: int = 10,
    ):
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.paper_manager = paper_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.max_iterations = max_iterations
        self.parser = ResponseParser()

        # ユーザーアクション待ち用
        self.user_action = None
        self.action_event = None

    async def run(
        self,
        paper_id: str,
        pdf_path: Path,
        tex_path: Path,
        websocket: WebSocket,
    ) -> Dict[str, Any]:
        """クリーン化を実行（WebSocket版）"""

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ1: クリーン化を開始 - {paper_id}",
            "level": "info"
        })

        # 除外項目リストを初期化
        excluded_items = self.data_manager.get_excluded_items(paper_id)

        iteration = 0
        stopped_reason = ""

        while iteration < self.max_iterations:
            iteration += 1

            await websocket.send_json({
                "type": "iteration_start",
                "iteration": iteration,
            })

            await websocket.send_json({
                "type": "log",
                "message": f"イテレーション {iteration} を開始",
                "level": "info"
            })

            # 除外項目リストを文字列に変換
            excluded_items_str = "\n".join(
                [f"- {item}" for item in excluded_items]
            ) if excluded_items else "なし"

            # プロンプトを構築
            prompt = self.prompt_template.format(
                excluded_items=excluded_items_str,
                checklist=self.checklist,
            )

            # 論文のバージョンを保存
            self.paper_manager.save_version(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                tex_path=tex_path,
                pdf_path=pdf_path,
            )

            # LLMを呼び出す
            await websocket.send_json({
                "type": "log",
                "message": "LLMに校正を依頼中...",
                "level": "info"
            })

            # LLM呼び出しの時間を計測
            start_time = time.time()
            llm_success = True
            response = ""

            try:
                response = self.llm_client.call(
                    prompt=prompt,
                    pdf_path=pdf_path,
                    tex_path=tex_path,
                )
            except Exception as e:
                llm_success = False
                response = f"Error: {str(e)}"
                await websocket.send_json({
                    "type": "error",
                    "message": f"LLM呼び出しエラー: {str(e)}",
                })
                raise
            finally:
                duration = time.time() - start_time

                # LLM呼び出しを記録
                self.data_manager.record_llm_call(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    model=self.llm_client.model,
                    provider=getattr(self.llm_client, 'provider', 'unknown'),
                    prompt_length=len(prompt),
                    response_length=len(response),
                    duration_seconds=duration,
                    success=llm_success,
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

            await websocket.send_json({
                "type": "llm_response",
                "message": "LLMの応答を受信しました",
            })

            # 「指摘事項はありません」が含まれているか確認
            if "指摘事項はありません" in response:
                await websocket.send_json({
                    "type": "log",
                    "message": "クリーン化完了（指摘事項なし）",
                    "level": "success"
                })

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

            # 応答をパースして指摘を抽出
            issues = self.parser.parse_proofreading_response(response)

            # 指摘が1つもない場合
            if not issues:
                await websocket.send_json({
                    "type": "log",
                    "message": "応答から指摘を抽出できませんでした",
                    "level": "warning"
                })

                await websocket.send_json({
                    "type": "log",
                    "message": f"生のLLM応答:\n{response[:500]}...",
                    "level": "info"
                })

                # パース失敗を記録
                self.data_manager.record_parse_failure(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    raw_response=response,
                    error_message="指摘の抽出に失敗しました",
                )

                # 次のイテレーションに進むか確認
                continue_choice = await self.wait_for_user_choice(
                    websocket,
                    "次のイテレーションに進みますか？",
                    ["Y", "N"]
                )

                # ユーザー選択を記録
                self.data_manager.record_user_action(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    action_type="continue_after_parse_failure",
                    action_value=continue_choice,
                    context="パース失敗後の継続確認",
                )

                if continue_choice != "Y":
                    stopped_reason = "parse_failed"
                    break
                continue

            # 修正点を表示
            await websocket.send_json({
                "type": "log",
                "message": f"修正点が検出されました: {len(issues)}件",
                "level": "info"
            })

            # インタラクティブな判断
            detected_in_iteration = []
            new_excluded = []

            for issue in issues:
                # 指摘を表示してアクションを待つ
                action = await self.get_user_action_for_issue(
                    websocket,
                    issue,
                    len(issues)
                )

                # 検出された指摘とユーザーアクションを記録
                self.data_manager.record_detected_issue(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    issue_number=issue.issue_number,
                    total_issues=len(issues),
                    before=issue.before,
                    reasoning=issue.reasoning,
                    after=issue.after,
                    user_action=action,
                )

                # ユーザーアクションを記録
                self.data_manager.record_user_action(
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    action_type="issue_judgment",
                    action_value=action,
                    context=f"issue_{issue.issue_number}/{len(issues)}",
                )

                if action == "A":
                    # 自動適用
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 自動適用します",
                        "level": "info"
                    })

                    success = self.paper_manager.apply_correction(
                        tex_path=tex_path,
                        before_text=issue.before,
                        after_text=issue.after,
                        backup=True,
                    )

                    if success:
                        detected_in_iteration.append(f"issue_{issue.issue_number}_auto")
                        await websocket.send_json({
                            "type": "log",
                            "message": "修正を適用しました",
                            "level": "success"
                        })
                    else:
                        detected_in_iteration.append(f"issue_{issue.issue_number}_manual")
                        await websocket.send_json({
                            "type": "log",
                            "message": "自動適用に失敗しました。手動で修正してください。",
                            "level": "warning"
                        })

                elif action == "M":
                    # 手動修正
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 手動で修正してください",
                        "level": "info"
                    })
                    detected_in_iteration.append(f"issue_{issue.issue_number}_manual")

                elif action == "S":
                    # スキップ
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: スキップ（誤検出として記録）",
                        "level": "info"
                    })

                elif action == "D":
                    # 判断困難
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 判断困難として記録",
                        "level": "warning"
                    })

                    # チェックリスト項目を入力（簡略化のため固定値）
                    item = f"item_issue_{issue.issue_number}"
                    reason = "判断困難"

                    new_excluded.append(item)
                    excluded_items.append(item)

                    self.data_manager.record_excluded_item(
                        paper_id=paper_id,
                        checklist_item=item,
                        reason=reason,
                        example_case=f"phase1_iteration_{iteration}_issue{issue.issue_number}",
                    )

                elif action == "Q":
                    # 中断
                    await websocket.send_json({
                        "type": "log",
                        "message": "クリーン化を中断します",
                        "level": "warning"
                    })
                    stopped_reason = "user_abort"
                    break

            # 中断判定 - 記録せずに終了
            if stopped_reason == "user_abort":
                break

            # 次のイテレーションに進むか確認
            continue_choice = await self.wait_for_user_choice(
                websocket,
                "次のイテレーションに進みますか？",
                ["Y", "N"]
            )

            # ユーザー選択を記録
            self.data_manager.record_user_action(
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                action_type="continue_to_next_iteration",
                action_value=continue_choice,
                context="イテレーション後の継続確認",
            )

            if continue_choice != "Y":
                stopped_reason = "user_stop"
                break

        # 最大反復回数に到達
        if iteration >= self.max_iterations and stopped_reason == "":
            stopped_reason = "max_iterations"
            await websocket.send_json({
                "type": "log",
                "message": f"最大反復回数（{self.max_iterations}）に到達しました",
                "level": "warning"
            })

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ1完了 - 総イテレーション数: {iteration}",
            "level": "success"
        })

        return {
            "iterations": iteration,
            "excluded_items_count": len(excluded_items),
            "stopped_reason": stopped_reason,
        }

    async def get_user_action_for_issue(
        self,
        websocket: WebSocket,
        issue: ProofreadingIssue,
        total_issues: int
    ) -> str:
        """指摘に対するユーザーアクションを取得"""

        # 指摘を表示
        await websocket.send_json({
            "type": "issue_detected",
            "issue": {
                "before": issue.before,
                "reasoning": issue.reasoning,
                "after": issue.after,
            },
            "issue_number": issue.issue_number,
            "total_issues": total_issues,
        })

        # ユーザーアクションを待つ
        self.action_event = asyncio.Event()
        self.user_action = None

        # ユーザーのアクションを待機（タイムアウトなし）
        await self.action_event.wait()

        return self.user_action

    async def wait_for_user_choice(
        self,
        websocket: WebSocket,
        message: str,
        choices: list
    ) -> str:
        """ユーザーの選択を待つ"""

        await websocket.send_json({
            "type": "user_choice_required",
            "message": message,
            "choices": choices,
        })

        self.action_event = asyncio.Event()
        self.user_action = None

        # ユーザーの選択を待機（タイムアウトなし）
        await self.action_event.wait()

        return self.user_action

    def set_user_action(self, action: str):
        """ユーザーアクションを設定"""
        self.user_action = action
        if self.action_event:
            self.action_event.set()


class WebSocketPhase3Adapter(WebSocketPhase1Adapter):
    """
    フェーズ3のWebSocketアダプター
    フェーズ1とほぼ同じロジックなので継承
    """

    async def run(
        self,
        paper_id: str,
        pdf_path: Path,
        tex_path: Path,
        websocket: WebSocket,
    ) -> Dict[str, Any]:
        """校正を実行（WebSocket版）"""

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ3: 校正を開始 - {paper_id}",
            "level": "info"
        })

        # phase1の実装をphase3として実行（phase名を変更）
        # ほぼ同じロジックなので、phase1の実装を流用
        result = await self._run_internal(
            paper_id=paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
            websocket=websocket,
            phase="phase3"
        )

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ3完了 - 総イテレーション数: {result['iterations']}",
            "level": "success"
        })

        return result

    async def _run_internal(
        self,
        paper_id: str,
        pdf_path: Path,
        tex_path: Path,
        websocket: WebSocket,
        phase: str,
    ) -> Dict[str, Any]:
        """内部実装（phase1とphase3で共通）"""

        excluded_items = self.data_manager.get_excluded_items(paper_id)
        iteration = 0
        stopped_reason = ""

        while iteration < self.max_iterations:
            iteration += 1

            await websocket.send_json({
                "type": "iteration_start",
                "iteration": iteration,
            })

            await websocket.send_json({
                "type": "log",
                "message": f"イテレーション {iteration} を開始",
                "level": "info"
            })

            excluded_items_str = "\n".join(
                [f"- {item}" for item in excluded_items]
            ) if excluded_items else "なし"

            prompt = self.prompt_template.format(
                excluded_items=excluded_items_str,
                checklist=self.checklist,
            )

            self.paper_manager.save_version(
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                tex_path=tex_path,
                pdf_path=pdf_path,
            )

            await websocket.send_json({
                "type": "log",
                "message": "LLMに校正を依頼中...",
                "level": "info"
            })

            # LLM呼び出しの時間を計測
            start_time = time.time()
            llm_success = True
            response = ""

            try:
                response = self.llm_client.call(
                    prompt=prompt,
                    pdf_path=pdf_path,
                    tex_path=tex_path,
                )
            except Exception as e:
                llm_success = False
                response = f"Error: {str(e)}"
                await websocket.send_json({
                    "type": "error",
                    "message": f"LLM呼び出しエラー: {str(e)}",
                })
                raise
            finally:
                duration = time.time() - start_time

                # LLM呼び出しを記録
                self.data_manager.record_llm_call(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    model=self.llm_client.model,
                    provider=getattr(self.llm_client, 'provider', 'unknown'),
                    prompt_length=len(prompt),
                    response_length=len(response),
                    duration_seconds=duration,
                    success=llm_success,
                )

            self.data_manager.save_prompt(
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                prompt=prompt,
            )
            self.data_manager.save_response(
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                response=response,
            )

            await websocket.send_json({
                "type": "llm_response",
                "message": "LLMの応答を受信しました",
            })

            if "指摘事項はありません" in response:
                await websocket.send_json({
                    "type": "log",
                    "message": "校正完了（指摘事項なし）",
                    "level": "success"
                })

                stopped_reason = "no_issues"

                self.data_manager.record_iteration(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )
                break

            issues = self.parser.parse_proofreading_response(response)

            if not issues:
                await websocket.send_json({
                    "type": "log",
                    "message": "応答から指摘を抽出できませんでした",
                    "level": "warning"
                })

                # パース失敗を記録
                self.data_manager.record_parse_failure(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    raw_response=response,
                    error_message="指摘の抽出に失敗しました",
                )

                continue_choice = await self.wait_for_user_choice(
                    websocket,
                    "次のイテレーションに進みますか？",
                    ["Y", "N"]
                )

                # ユーザー選択を記録
                self.data_manager.record_user_action(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    action_type="continue_after_parse_failure",
                    action_value=continue_choice,
                    context="パース失敗後の継続確認",
                )

                if continue_choice != "Y":
                    stopped_reason = "parse_failed"
                    break
                continue

            await websocket.send_json({
                "type": "log",
                "message": f"修正点が検出されました: {len(issues)}件",
                "level": "info"
            })

            detected_in_iteration = []
            new_excluded = []

            for issue in issues:
                action = await self.get_user_action_for_issue(
                    websocket,
                    issue,
                    len(issues)
                )

                # 検出された指摘とユーザーアクションを記録
                self.data_manager.record_detected_issue(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    issue_number=issue.issue_number,
                    total_issues=len(issues),
                    before=issue.before,
                    reasoning=issue.reasoning,
                    after=issue.after,
                    user_action=action,
                )

                # ユーザーアクションを記録
                self.data_manager.record_user_action(
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    action_type="issue_judgment",
                    action_value=action,
                    context=f"issue_{issue.issue_number}/{len(issues)}",
                )

                if action == "A":
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 自動適用します",
                        "level": "info"
                    })

                    success = self.paper_manager.apply_correction(
                        tex_path=tex_path,
                        before_text=issue.before,
                        after_text=issue.after,
                        backup=True,
                    )

                    if success:
                        detected_in_iteration.append(f"issue_{issue.issue_number}_auto")
                        await websocket.send_json({
                            "type": "log",
                            "message": "修正を適用しました",
                            "level": "success"
                        })
                    else:
                        detected_in_iteration.append(f"issue_{issue.issue_number}_manual")
                        await websocket.send_json({
                            "type": "log",
                            "message": "自動適用に失敗しました",
                            "level": "warning"
                        })

                elif action == "M":
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 手動で修正してください",
                        "level": "info"
                    })
                    detected_in_iteration.append(f"issue_{issue.issue_number}_manual")

                elif action == "S":
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: スキップ",
                        "level": "info"
                    })

                elif action == "D":
                    await websocket.send_json({
                        "type": "log",
                        "message": f"指摘 {issue.issue_number}: 判断困難として記録",
                        "level": "warning"
                    })

                    item = f"item_issue_{issue.issue_number}"
                    reason = "判断困難"

                    new_excluded.append(item)
                    excluded_items.append(item)

                    self.data_manager.record_excluded_item(
                        paper_id=paper_id,
                        checklist_item=item,
                        reason=reason,
                        example_case=f"{phase}_iteration_{iteration}_issue{issue.issue_number}",
                    )

                elif action == "Q":
                    await websocket.send_json({
                        "type": "log",
                        "message": "校正を中断します",
                        "level": "warning"
                    })
                    stopped_reason = "user_abort"
                    break

            # 中断判定 - 記録せずに終了
            if stopped_reason == "user_abort":
                break

            # 次のイテレーションに進むか確認
            continue_choice = await self.wait_for_user_choice(
                websocket,
                "次のイテレーションに進みますか？",
                ["Y", "N"]
            )

            # ユーザー選択を記録
            self.data_manager.record_user_action(
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                action_type="continue_to_next_iteration",
                action_value=continue_choice,
                context="イテレーション後の継続確認",
            )

            if continue_choice != "Y":
                stopped_reason = "user_stop"
                break

        if iteration >= self.max_iterations and stopped_reason == "":
            stopped_reason = "max_iterations"
            await websocket.send_json({
                "type": "log",
                "message": f"最大反復回数（{self.max_iterations}）に到達しました",
                "level": "warning"
            })

        return {
            "iterations": iteration,
            "excluded_items_count": len(excluded_items),
            "stopped_reason": stopped_reason,
        }
