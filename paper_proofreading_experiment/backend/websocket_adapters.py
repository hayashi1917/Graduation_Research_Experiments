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
from phase2_embedder import Phase2Embedder


class WebSocketPhase1Adapter:
    """フェーズ1のWebSocketアダプター"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        paper_manager: PaperManager,
        prompt_template: str,
        checklist: str,
        versions_dir: Path = None,
    ):
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.paper_manager = paper_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.versions_dir = versions_dir
        self.parser = ResponseParser()

        # ユーザーアクション待ち用
        self.user_action = None
        self.user_action_payload = None
        self.action_event = None

    @staticmethod
    def _normalize_issue_action(action: str) -> str:
        mapping = {
            "A": "accept",
            "M": "manual_fix",
            "S": "skip",
            "Q": "abort",
        }
        return mapping.get(action, action)

    @staticmethod
    def _is_detection_action(action: str) -> bool:
        return action in {"A", "M"}

    async def run(
        self,
        paper_id: str,
        pdf_path: Path,
        websocket: WebSocket,
    ) -> Dict[str, Any]:
        """クリーン化を実行（WebSocket版）"""

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ1: クリーン化を開始 - {paper_id}",
            "level": "info"
        })

        # 進捗を読み込む（前回の続きから開始）
        saved_phase1_id, saved_iteration, saved_excluded_items = self.data_manager.load_progress(paper_id, "phase1")

        if saved_iteration > 0:
            # 進捗から再開
            await websocket.send_json({
                "type": "log",
                "message": f"前回の進捗を検出: Phase1 {saved_phase1_id}、イテレーション {saved_iteration} から再開します",
                "level": "info"
            })
            phase1_id = saved_phase1_id
            iteration = saved_iteration
            excluded_items = saved_excluded_items
        else:
            # 新規開始 - 新しいPhase1 IDを生成
            phase1_id = self.data_manager.generate_phase1_id()
            iteration = 0
            excluded_items = []  # 新セッションは空の除外リストから開始

            # Phase1セッション情報を保存
            from datetime import datetime
            started_at = datetime.now().isoformat()
            self.data_manager.save_phase1_session(
                phase1_id=phase1_id,
                paper_id=paper_id,
                started_at=started_at,
                status="in_progress",
            )

            # Phase1開始をsessions.jsonにも記録
            self.data_manager.save_session_metadata(
                session_id=phase1_id,
                paper_id=paper_id,
                phase1_start=started_at,
            )

            await websocket.send_json({
                "type": "log",
                "message": f"新しいPhase1を開始: {phase1_id}",
                "level": "info"
            })

        stopped_reason = ""

        while True:
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
                    session_id=phase1_id,
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

            # 応答をパースして指摘を抽出
            parse_result = self.parser.parse_proofreading_response(response)

            if parse_result.no_issues:
                await websocket.send_json({
                    "type": "log",
                    "message": "クリーン化完了（指摘事項なし）",
                    "level": "success"
                })

                stopped_reason = "no_issues"

                self.data_manager.record_iteration(
                    session_id=phase1_id,
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )

                # 完了したので進捗をクリア
                self.data_manager.clear_progress(paper_id, "phase1")
                break

            issues = parse_result.issues

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
                    session_id=phase1_id,
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
                    session_id=phase1_id,
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    action_type="continue_after_parse_failure",
                    action_value=continue_choice,
                    context="パース失敗後の継続確認",
                )

                # パース失敗時もイテレーション結果を記録
                if continue_choice != "Y":
                    stopped_reason = "parse_failed"
                else:
                    stopped_reason = ""  # 継続中

                self.data_manager.record_iteration(
                    session_id=phase1_id,
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )

                if continue_choice != "Y":
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
                while True:
                    action, action_payload = await self.get_user_action_for_issue(
                        websocket,
                        issue,
                        len(issues)
                    )

                    if action not in {"A", "M", "S", "Q"}:

                        await websocket.send_json({
                            "type": "log",
                            "message": "無効なアクションです。もう一度選択してください。",
                            "level": "error"
                        })
                        continue

                    self.data_manager.record_detected_issue(
                        session_id=phase1_id,
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

                    self.data_manager.record_user_action(
                        session_id=phase1_id,
                        paper_id=paper_id,
                        phase="phase1",
                        iteration=iteration,
                        action_type="issue_judgment",
                        action_value=action,
                        context=f"issue_{issue.issue_number}/{len(issues)}",
                    )

                    if action == "A":
                        await websocket.send_json({
                            "type": "log",
                            "message": f"指摘 {issue.issue_number}: 承認として記録",
                            "level": "info"
                        })
                        detected_in_iteration.append(f"issue_{issue.issue_number}_accepted")
                        break


                    if action == "M":
                        await websocket.send_json({
                            "type": "log",
                            "message": f"指摘 {issue.issue_number}: 手動で修正してください",
                            "level": "info"
                        })
                        detected_in_iteration.append(f"issue_{issue.issue_number}_manual")
                        break

                    if action == "S":
                        checklist_item = (action_payload or {}).get("checklist_item", "").strip()
                        reason = (action_payload or {}).get("reason", "").strip() or "スキップ（誤検出）"

                        if not checklist_item:
                            await websocket.send_json({
                                "type": "log",
                                "message": "除外するチェックリスト項目名が入力されていません。もう一度入力してください。",
                                "level": "error"
                            })
                            continue

                        if checklist_item in excluded_items:
                            await websocket.send_json({
                                "type": "log",
                                "message": f"指摘 {issue.issue_number}: '{checklist_item}' は既に除外済みです",
                                "level": "warning",
                            })
                            continue

                        await websocket.send_json({
                            "type": "log",
                            "message": f"指摘 {issue.issue_number}: '{checklist_item}' を除外に追加しました",
                            "level": "info"
                        })

                        new_excluded.append(checklist_item)
                        excluded_items.append(checklist_item)

                        self.data_manager.record_excluded_item(
                            session_id=phase1_id,
                            paper_id=paper_id,
                            checklist_item=checklist_item,
                            reason=reason,
                            example_case=f"phase1_iteration_{iteration}_issue{issue.issue_number}",
                        )
                        break

                    # action == "Q"
                    await websocket.send_json({
                        "type": "log",
                        "message": "クリーン化を中断します",
                        "level": "warning"
                    })
                    stopped_reason = "user_abort"
                    break

                if stopped_reason == "user_abort":
                    break

            # 中断判定
            if stopped_reason == "user_abort":
                # 中断時もイテレーション結果を記録
                self.data_manager.record_iteration(
                    session_id=phase1_id,
                    paper_id=paper_id,
                    phase="phase1",
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=detected_in_iteration,
                    new_issues_count=len(issues),
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )
                break

            # 次のイテレーションに進むか確認
            continue_choice = await self.wait_for_user_choice(
                websocket,
                "次のイテレーションに進みますか？",
                ["Y", "N"]
            )

            # ユーザー選択を記録
            self.data_manager.record_user_action(
                session_id=phase1_id,
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                action_type="continue_to_next_iteration",
                action_value=continue_choice,
                context="イテレーション後の継続確認",
            )

            # イテレーション結果を記録（継続/停止にかかわらず）
            if continue_choice != "Y":
                stopped_reason = "user_stop"
            else:
                stopped_reason = ""  # 継続中

            self.data_manager.record_iteration(
                session_id=phase1_id,
                paper_id=paper_id,
                phase="phase1",
                iteration=iteration,
                llm_model=self.llm_client.model,
                detected_errors=detected_in_iteration,
                new_issues_count=len(issues),
                excluded_items=excluded_items,
                stopped_reason=stopped_reason,
            )

            if continue_choice != "Y":
                # 中断時は進捗を保存（次回このイテレーションから再開）
                self.data_manager.save_progress(
                    paper_id=paper_id,
                    phase="phase1",
                    session_id=phase1_id,
                    iteration=iteration,
                    excluded_items=excluded_items,
                )
                break

            # 次のイテレーションに進む場合も進捗を保存
            self.data_manager.save_progress(
                paper_id=paper_id,
                phase="phase1",
                session_id=phase1_id,
                iteration=iteration,
                excluded_items=excluded_items,
            )

            # 次のイテレーションに進む前に、手動修正を確認
            # Note: PDFファイルは直接編集できないため、手動修正は別途実施が必要
            await websocket.send_json({
                "type": "log",
                "message": "手動修正がある場合は、PDFファイルを更新してから次のイテレーションに進んでください",
                "level": "info"
            })

        # Phase1セッション情報を更新
        from datetime import datetime
        completed_at = datetime.now().isoformat()
        final_status = "completed" if stopped_reason in ["no_issues", "user_stop"] else "aborted"

        # 最終バージョンを保存
        final_version_dir = self.versions_dir / paper_id / "phase1" / phase1_id
        final_version_dir.mkdir(parents=True, exist_ok=True)

        final_pdf_path = final_version_dir / "final.pdf"

        # PDFファイルをコピー
        import shutil
        if pdf_path.exists():
            shutil.copy2(pdf_path, final_pdf_path)

        # Phase1セッション情報を更新
        self.data_manager.update_phase1_session(
            phase1_id=phase1_id,
            completed_at=completed_at,
            iterations=iteration,
            excluded_items=excluded_items,
            status=final_status,
            final_pdf_path=str(final_pdf_path) if pdf_path.exists() else "",
        )

        # sessions.jsonのメタデータも更新
        self.data_manager.update_session_metadata(
            session_id=phase1_id,
            paper_id=paper_id,
            phase1_end=completed_at,
        )

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ1完了 - 総イテレーション数: {iteration}, ステータス: {final_status}",
            "level": "success"
        })

        return {
            "phase1_id": phase1_id,
            "iterations": iteration,
            "excluded_items_count": len(excluded_items),
            "stopped_reason": stopped_reason,
            "status": final_status,
        }

    async def get_user_action_for_issue(
        self,
        websocket: WebSocket,
        issue: ProofreadingIssue,
        total_issues: int
    ) -> tuple[str, dict]:
        """指摘に対するユーザーアクションを取得"""

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

        return await self._wait_for_user_action()

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

        action, _ = await self._wait_for_user_action()
        return action

    async def _wait_for_user_action(self) -> tuple[str, dict]:
        """ユーザーアクションが送られるまで待機"""

        self.action_event = asyncio.Event()
        self.user_action = None
        self.user_action_payload = None

        await self.action_event.wait()

        return self.user_action, self.user_action_payload or {}

    def set_user_action(self, action: str, payload: Optional[Dict[str, Any]] = None):
        """ユーザーアクションを設定"""
        self.user_action = action
        self.user_action_payload = payload
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
        websocket: WebSocket,
        phase: str,
    ) -> Dict[str, Any]:
        """内部実装（phase1とphase3で共通）"""

        # 進捗を読み込む（前回の続きから開始）
        saved_session_id, saved_iteration, saved_excluded_items = self.data_manager.load_progress(paper_id, phase)

        if saved_iteration > 0:
            # 進捗から再開
            await websocket.send_json({
                "type": "log",
                "message": f"前回の進捗を検出: セッション {saved_session_id}、イテレーション {saved_iteration} から再開します",
                "level": "info"
            })
            session_id = saved_session_id
            iteration = saved_iteration
            excluded_items = saved_excluded_items
        else:
            # 新規開始 - 最新のセッションIDを取得（Phase1で作成されたもの）
            session_id = self.data_manager.get_latest_session_id(paper_id)
            if not session_id:
                # セッションが存在しない場合はエラー
                await websocket.send_json({
                    "type": "error",
                    "message": "エラー: Phase1のセッションが見つかりません。先にPhase1を実行してください。",
                })
                raise ValueError("Phase1のセッションが見つかりません")

            iteration = 0
            # セッションIDに紐づく除外項目を取得
            excluded_items = self.data_manager.get_excluded_items(paper_id, session_id)

            await websocket.send_json({
                "type": "log",
                "message": f"セッション {session_id} の除外項目を使用します（{len(excluded_items)}件）",
                "level": "info"
            })

        stopped_reason = ""

        embedded_error_state: Dict[str, Dict[str, Any]] = {}
        if phase == "phase3":
            embedded_error_state = self.data_manager.load_embedded_error_state(
                session_id=session_id,
                paper_id=paper_id,
            )
            if iteration > 0:
                self.data_manager.mark_detected_errors_from_history(
                    session_id=session_id,
                    paper_id=paper_id,
                    phase=phase,
                    max_iteration=iteration,
                    embedded_errors=embedded_error_state,
                )

        while True:
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
                    session_id=session_id,
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

            parse_result = self.parser.parse_proofreading_response(response)

            if parse_result.no_issues:
                await websocket.send_json({
                    "type": "log",
                    "message": "校正完了（指摘事項なし）",
                    "level": "success"
                })

                stopped_reason = "no_issues"

                self.data_manager.record_iteration(
                    session_id=session_id,
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )

                # 完了したので進捗をクリア
                self.data_manager.clear_progress(paper_id, phase)
                break

            issues = parse_result.issues

            if not issues:
                await websocket.send_json({
                    "type": "log",
                    "message": "応答から指摘を抽出できませんでした",
                    "level": "warning"
                })

                # パース失敗を記録
                self.data_manager.record_parse_failure(
                    session_id=session_id,
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
                    session_id=session_id,
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    action_type="continue_after_parse_failure",
                    action_value=continue_choice,
                    context="パース失敗後の継続確認",
                )

                # パース失敗時もイテレーション結果を記録
                if continue_choice != "Y":
                    stopped_reason = "parse_failed"
                else:
                    stopped_reason = ""  # 継続中

                self.data_manager.record_iteration(
                    session_id=session_id,
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=[],
                    new_issues_count=0,
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )

                if continue_choice != "Y":
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
                while True:
                    action, action_payload = await self.get_user_action_for_issue(
                        websocket,
                        issue,
                        len(issues)
                    )

                    if action not in {"A", "M", "S", "Q"}:
                        await websocket.send_json({
                            "type": "log",
                            "message": "無効なアクションです。もう一度選択してください。",
                            "level": "error"
                        })
                        continue

                    normalized_action = self._normalize_issue_action(action)

                    self.data_manager.record_detected_issue(
                        session_id=session_id,
                        paper_id=paper_id,
                        phase=phase,
                        iteration=iteration,
                        issue_number=issue.issue_number,
                        total_issues=len(issues),
                        before=issue.before,
                        reasoning=issue.reasoning,
                        after=issue.after,
                        user_action=normalized_action,
                    )

                    self.data_manager.record_user_action(
                        session_id=session_id,
                        paper_id=paper_id,
                        phase=phase,
                        iteration=iteration,
                        action_type="issue_judgment",
                        action_value=action,
                        context=f"issue_{issue.issue_number}/{len(issues)}",
                    )

                    if self._is_detection_action(action):
                        await websocket.send_json({
                            "type": "log",
                            "message": f"指摘 {issue.issue_number}: {'承認' if action == 'A' else '手動修正'}を選択",
                            "level": "info"
                        })
                        matched_error_id = None
                        if embedded_error_state:
                            matched_error_id = self.data_manager.find_matching_embedded_error(
                                embedded_error_state,
                                detected_before=issue.before,
                                detected_after=issue.after,
                            )
                            if matched_error_id:
                                embedded_error_state[matched_error_id]["detected"] = True
                                embedded_error_state[matched_error_id]["detected_iteration"] = iteration
                                checklist_item = embedded_error_state[matched_error_id][
                                    "checklist_item"
                                ]
                                self.data_manager.record_detected_embedded_error(
                                    session_id=session_id,
                                    paper_id=paper_id,
                                    phase=phase,
                                    iteration=iteration,
                                    issue_number=issue.issue_number,
                                    embedded_error_id=matched_error_id,
                                    checklist_item=checklist_item,
                                    action=normalized_action,
                                )

                        label = (
                            f"issue_{issue.issue_number}_"
                            f"{'accepted' if action == 'A' else 'manual'}"
                        )
                        if matched_error_id:
                            label = f"{label}_error_{matched_error_id}"

                        detected_in_iteration.append(label)
                        break

                    if action == "S":
                        checklist_item = (action_payload or {}).get("checklist_item", "").strip()
                        reason = (action_payload or {}).get("reason", "").strip() or "スキップ（誤検出）"

                        if not checklist_item:
                            await websocket.send_json({
                                "type": "log",
                                "message": "除外するチェックリスト項目名が入力されていません。もう一度入力してください。",
                                "level": "error"
                            })
                            continue

                        if checklist_item in excluded_items:
                            await websocket.send_json({
                                "type": "log",
                                "message": f"指摘 {issue.issue_number}: '{checklist_item}' は既に除外済みです",
                                "level": "warning",
                            })
                            continue

                        await websocket.send_json({
                            "type": "log",
                            "message": f"指摘 {issue.issue_number}: '{checklist_item}' を除外に追加しました",
                            "level": "info"
                        })

                        new_excluded.append(checklist_item)
                        excluded_items.append(checklist_item)

                        self.data_manager.record_excluded_item(
                            session_id=session_id,
                            paper_id=paper_id,
                            checklist_item=checklist_item,
                            reason=reason,
                            example_case=f"{phase}_iteration_{iteration}_issue{issue.issue_number}",
                        )
                        break

                    # action == "Q"
                    await websocket.send_json({
                        "type": "log",
                        "message": "校正を中断します",
                        "level": "warning"
                    })
                    stopped_reason = "user_abort"
                    break

                if stopped_reason == "user_abort":
                    break

            # 中断判定
            if stopped_reason == "user_abort":
                # 中断時もイテレーション結果を記録
                self.data_manager.record_iteration(
                    session_id=session_id,
                    paper_id=paper_id,
                    phase=phase,
                    iteration=iteration,
                    llm_model=self.llm_client.model,
                    detected_errors=detected_in_iteration,
                    new_issues_count=len(issues),
                    excluded_items=excluded_items,
                    stopped_reason=stopped_reason,
                )
                break

            # 次のイテレーションに進むか確認
            continue_choice = await self.wait_for_user_choice(
                websocket,
                "次のイテレーションに進みますか？",
                ["Y", "N"]
            )

            # ユーザー選択を記録
            self.data_manager.record_user_action(
                session_id=session_id,
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                action_type="continue_to_next_iteration",
                action_value=continue_choice,
                context="イテレーション後の継続確認",
            )

            # イテレーション結果を記録（継続/停止にかかわらず）
            if continue_choice != "Y":
                stopped_reason = "user_stop"
            else:
                stopped_reason = ""  # 継続中

            self.data_manager.record_iteration(
                session_id=session_id,
                paper_id=paper_id,
                phase=phase,
                iteration=iteration,
                llm_model=self.llm_client.model,
                detected_errors=detected_in_iteration,
                new_issues_count=len(issues),
                excluded_items=excluded_items,
                stopped_reason=stopped_reason,
            )

            if continue_choice != "Y":
                # 中断時は進捗を保存（次回このイテレーションから再開）
                self.data_manager.save_progress(
                    paper_id=paper_id,
                    phase=phase,
                    session_id=session_id,
                    iteration=iteration,
                    excluded_items=excluded_items,
                )
                break

            # 次のイテレーションに進む場合も進捗を保存
            self.data_manager.save_progress(
                paper_id=paper_id,
                phase=phase,
                session_id=session_id,
                iteration=iteration,
                excluded_items=excluded_items,
            )

        if phase == "phase3":
            from datetime import datetime
            self.data_manager.update_session_metadata(
                session_id=session_id,
                paper_id=paper_id,
                phase3_end=datetime.now().isoformat(),
            )

        return {
            "iterations": iteration,
            "excluded_items_count": len(excluded_items),
            "stopped_reason": stopped_reason,
        }


class WebSocketPhase2Adapter:
    """フェーズ2のWebSocketアダプター（誤り埋め込み）"""

    def __init__(
        self,
        llm_client: LLMClient,
        data_manager: DataManager,
        prompt_template: str,
        checklist: str,
        num_errors: int = 10,
    ):
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.prompt_template = prompt_template
        self.checklist = checklist
        self.num_errors = num_errors

    async def run(
        self,
        paper_id: str,
        pdf_path: Path,
        websocket: WebSocket,
    ) -> Dict[str, Any]:
        """誤り埋め込みを実行（WebSocket版）"""

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ2: 誤り埋め込みを開始 - {paper_id}",
            "level": "info"
        })

        # TODO: Phase1セッション選択機能
        # 将来的には、ユーザーがどのPhase1セッションを使用するか選択できるようにする
        # phase1_sessions = self.data_manager.get_phase1_sessions(paper_id)
        # selected_phase1 = phase1_sessions[0] if phase1_sessions else None

        # 最新のセッションIDを取得（Phase1で作成されたもの）
        # Note: 現在は古いsessions.jsonベースのセッション管理を使用
        # Phase1セッション（phase1_sessions.json）への移行が必要
        session_id = self.data_manager.get_latest_session_id(paper_id)
        if not session_id:
            # セッションが存在しない場合はエラー
            await websocket.send_json({
                "type": "error",
                "message": "エラー: Phase1のセッションが見つかりません。先にPhase1を実行してください。",
            })
            raise ValueError("Phase1のセッションが見つかりません")

        await websocket.send_json({
            "type": "log",
            "message": f"セッション {session_id} を使用します",
            "level": "info"
        })

        # セッションIDに紐づく除外項目を取得
        excluded_items = self.data_manager.get_excluded_items(paper_id, session_id)

        await websocket.send_json({
            "type": "log",
            "message": f"除外項目: {len(excluded_items)}件",
            "level": "info"
        })

        # Phase2Embedderを作成
        embedder = Phase2Embedder(
            llm_client=self.llm_client,
            data_manager=self.data_manager,
            prompt_template=self.prompt_template,
            checklist=self.checklist,
            num_errors=self.num_errors,
            excluded_items=excluded_items,
        )

        # 除外項目のリストを文字列に変換
        excluded_items_str = "\n".join(
            [f"- {item}" for item in excluded_items]
        ) if excluded_items else "なし"

        # プロンプトを構築
        prompt = self.prompt_template.format(
            excluded_items=excluded_items_str,
            checklist=self.checklist,
        )

        # LLMを呼び出す
        await websocket.send_json({
            "type": "log",
            "message": "LLMに誤り埋め込みを依頼中...",
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
                session_id=session_id,
                paper_id=paper_id,
                phase="phase2",
                iteration=1,
                model=self.llm_client.model,
                provider=getattr(self.llm_client, 'provider', 'unknown'),
                prompt_length=len(prompt),
                response_length=len(response),
                duration_seconds=duration,
                success=llm_success,
            )

        # 応答を保存
        self.data_manager.save_response(
            paper_id=paper_id,
            phase="phase2",
            iteration=1,
            response=response,
        )
        self.data_manager.save_prompt(
            paper_id=paper_id,
            phase="phase2",
            iteration=1,
            prompt=prompt,
        )

        await websocket.send_json({
            "type": "log",
            "message": "LLMの応答を受信しました",
            "level": "info"
        })

        # JSONを抽出してパース
        errors = embedder._parse_errors_from_response(response)

        if not errors:
            await websocket.send_json({
                "type": "error",
                "message": "誤りの抽出に失敗しました。応答を確認して、手動で誤りを記録してください。",
            })
            return {"errors": [], "success": False, "count": 0}

        # 誤りをデータベースに記録
        await websocket.send_json({
            "type": "log",
            "message": f"{len(errors)}件の誤りを記録します",
            "level": "info"
        })

        for i, error in enumerate(errors, 1):
            # 各誤りをWebSocketで送信
            await websocket.send_json({
                "type": "embedded_error",
                "error": {
                    "error_id": error.get("error_id", i),
                    "checklist_item": error.get("checklist_item", ""),
                    "category": error.get("category", ""),
                    "before": error.get("before", ""),
                    "after": error.get("after", ""),
                    "location": error.get("location", ""),
                    "description": error.get("description", ""),
                },
                "index": i,
                "total": len(errors),
            })

            # CSVに記録
            self.data_manager.record_embedded_error(
                session_id=session_id,
                paper_id=paper_id,
                error_id=error.get("error_id", i),
                checklist_item=error.get("checklist_item", ""),
                category=error.get("category", ""),
                before=error.get("before", ""),
                after=error.get("after", ""),
                location=error.get("location", ""),
            )

        await websocket.send_json({
            "type": "log",
            "message": "誤りの記録完了",
            "level": "success"
        })

        # セッションメタデータを更新（Phase2完了）
        from datetime import datetime
        self.data_manager.update_session_metadata(
            session_id=session_id,
            paper_id=paper_id,
            phase2_end=datetime.now().isoformat(),
        )

        await websocket.send_json({
            "type": "log",
            "message": f"フェーズ2完了 - 埋め込まれた誤り数: {len(errors)}",
            "level": "success"
        })

        return {
            "errors": errors,
            "success": True,
            "count": len(errors),
            "session_id": session_id,
        }
