"""
データ管理モジュール
実験データをCSVファイルに記録する
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class DataManager:
    """実験データの記録を管理するクラス"""

    def __init__(self, results_dir: Path):
        """
        Args:
            results_dir: 結果を保存するディレクトリ
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # CSVファイルのパス
        self.embedded_errors_csv = self.results_dir / "embedded_errors.csv"
        self.iteration_log_csv = self.results_dir / "iteration_log.csv"
        self.excluded_items_csv = self.results_dir / "excluded_items.csv"
        self.summary_csv = self.results_dir / "summary.csv"
        self.detected_issues_csv = self.results_dir / "detected_issues.csv"
        self.parse_failures_csv = self.results_dir / "parse_failures.csv"
        self.llm_calls_csv = self.results_dir / "llm_calls.csv"
        self.user_actions_csv = self.results_dir / "user_actions.csv"
        self.detection_rates_csv = self.results_dir / "detection_rates.csv"

        # 進捗ファイルのパス
        self.progress_file = self.results_dir / "progress.json"

        # セッションメタデータファイルのパス
        self.sessions_file = self.results_dir / "sessions.json"

        # Phase1セッション管理ファイルのパス
        self.phase1_sessions_file = self.results_dir / "phase1_sessions.json"

        # CSVファイルを初期化
        self._initialize_csv_files()

    def _safe_load_json(self, file_path: Path, default: Any = None) -> Any:
        """
        JSONファイルを安全に読み込む

        Args:
            file_path: 読み込むJSONファイルのパス
            default: ファイルが存在しない、空、または破損している場合のデフォルト値

        Returns:
            パースされたJSONデータ、またはデフォルト値
        """
        if not file_path.exists():
            return default if default is not None else {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    # ファイルが空の場合
                    return default if default is not None else {}
                return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            # JSONパースエラーまたはその他のエラー
            print(f"Warning: Failed to load JSON from {file_path}: {e}")
            return default if default is not None else {}

    def _initialize_csv_files(self):
        """CSVファイルを初期化（ヘッダー行を作成）"""

        # embedded_errors.csv
        if not self.embedded_errors_csv.exists():
            with open(self.embedded_errors_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "error_id",
                    "checklist_item",
                    "category",
                    "before",
                    "after",
                    "location",
                    "timestamp",
                ])

        # iteration_log.csv
        if not self.iteration_log_csv.exists():
            with open(self.iteration_log_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "timestamp",
                    "llm_model",
                    "detected_errors",
                    "new_issues_count",
                    "excluded_items",
                    "stopped_reason",
                ])

        # excluded_items.csv
        if not self.excluded_items_csv.exists():
            with open(self.excluded_items_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "checklist_item",
                    "reason",
                    "timestamp",
                    "example_case",
                ])

        # summary.csv
        if not self.summary_csv.exists():
            with open(self.summary_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "total_embedded",
                    "total_detected",
                    "detection_rate",
                    "phase1_iterations",
                    "phase3_iterations",
                    "excluded_items_count",
                    "completion_time",
                ])

        # detected_issues.csv
        if not self.detected_issues_csv.exists():
            with open(self.detected_issues_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "issue_number",
                    "total_issues",
                    "before",
                    "reasoning",
                    "after",
                    "user_action",
                    "timestamp",
                ])

        # parse_failures.csv
        if not self.parse_failures_csv.exists():
            with open(self.parse_failures_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "raw_response_preview",
                    "error_message",
                    "timestamp",
                ])

        # llm_calls.csv
        if not self.llm_calls_csv.exists():
            with open(self.llm_calls_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "model",
                    "provider",
                    "prompt_length",
                    "response_length",
                    "duration_seconds",
                    "success",
                    "timestamp",
                ])

        # user_actions.csv
        if not self.user_actions_csv.exists():
            with open(self.user_actions_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "action_type",
                    "action_value",
                    "context",
                    "timestamp",
                ])

        # detection_rates.csv
        if not self.detection_rates_csv.exists():
            with open(self.detection_rates_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id",
                    "paper_id",
                    "phase",
                    "iteration",
                    "checklist_item",
                    "detected_iteration",
                    "cumulative_detection_rate",
                    "timestamp",
                ])

    def record_embedded_error(
        self,
        session_id: str,
        paper_id: str,
        error_id: int,
        checklist_item: str,
        category: str,
        before: str,
        after: str,
        location: str,
    ):
        """埋め込まれた誤りを記録"""
        timestamp = datetime.now().isoformat()

        with open(self.embedded_errors_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                error_id,
                checklist_item,
                category,
                before,
                after,
                location,
                timestamp,
            ])

    def record_iteration(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        llm_model: str,
        detected_errors: List[str],
        new_issues_count: int,
        excluded_items: List[str],
        stopped_reason: str = "",
    ):
        """イテレーションのログを記録"""
        timestamp = datetime.now().isoformat()

        with open(self.iteration_log_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                timestamp,
                llm_model,
                json.dumps(detected_errors, ensure_ascii=False),
                new_issues_count,
                json.dumps(excluded_items, ensure_ascii=False),
                stopped_reason,
            ])

    def record_excluded_item(
        self,
        session_id: str,
        paper_id: str,
        checklist_item: str,
        reason: str,
        example_case: str = "",
    ):
        """除外されたチェックリスト項目を記録"""
        timestamp = datetime.now().isoformat()

        with open(self.excluded_items_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                checklist_item,
                reason,
                timestamp,
                example_case,
            ])

    def record_detected_issue(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        issue_number: int,
        total_issues: int,
        before: str,
        reasoning: str,
        after: str,
        user_action: str,
    ):
        """検出された個別の指摘事項を記録"""
        timestamp = datetime.now().isoformat()

        with open(self.detected_issues_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                issue_number,
                total_issues,
                before,
                reasoning,
                after,
                user_action,
                timestamp,
            ])

    def record_parse_failure(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        raw_response: str,
        error_message: str,
    ):
        """パース失敗を記録"""
        timestamp = datetime.now().isoformat()

        # レスポンスが長い場合は最初の500文字のみ保存
        response_preview = raw_response[:500] if len(raw_response) > 500 else raw_response

        with open(self.parse_failures_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                response_preview,
                error_message,
                timestamp,
            ])

    def record_llm_call(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        model: str,
        provider: str,
        prompt_length: int,
        response_length: int,
        duration_seconds: float,
        success: bool,
    ):
        """LLM API呼び出しを記録"""
        timestamp = datetime.now().isoformat()

        with open(self.llm_calls_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                model,
                provider,
                prompt_length,
                response_length,
                duration_seconds,
                success,
                timestamp,
            ])

    def record_user_action(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        action_type: str,
        action_value: str,
        context: str = "",
    ):
        """ユーザーアクションを記録"""
        timestamp = datetime.now().isoformat()

        with open(self.user_actions_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                action_type,
                action_value,
                context,
                timestamp,
            ])

    def record_summary(
        self,
        session_id: str,
        paper_id: str,
        total_embedded: int,
        total_detected: int,
        detection_rate: float,
        phase1_iterations: int,
        phase3_iterations: int,
        excluded_items_count: int,
        completion_time: str,
    ):
        """サマリー情報を記録"""
        with open(self.summary_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                total_embedded,
                total_detected,
                detection_rate,
                phase1_iterations,
                phase3_iterations,
                excluded_items_count,
                completion_time,
            ])

    def record_detection_rate(
        self,
        session_id: str,
        paper_id: str,
        phase: str,
        iteration: int,
        checklist_item: str,
        detected_iteration: int,
        cumulative_detection_rate: float,
    ):
        """検出率情報を記録"""
        timestamp = datetime.now().isoformat()

        with open(self.detection_rates_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                paper_id,
                phase,
                iteration,
                checklist_item,
                detected_iteration,
                cumulative_detection_rate,
                timestamp,
            ])

    def calculate_detection_rates(
        self, session_id: str, paper_id: str, phase: str, current_iteration: int
    ) -> Dict[str, Any]:
        """指定されたセッションとイテレーションまでの検出率を計算

        Args:
            session_id: セッションID
            paper_id: 論文ID
            phase: フェーズ (phase3)
            current_iteration: 現在のイテレーション番号

        Returns:
            {
                "total_embedded": 埋め込まれた誤りの総数,
                "total_detected": 検出された誤りの総数,
                "detection_rate": 全体検出率（%）,
                "items_detection": {
                    "checklist_item": {
                        "detected_iteration": 検出されたイテレーション番号 (0=未検出),
                        "detected": True/False
                    },
                    ...
                }
            }
        """
        # 埋め込まれた誤りを取得（このセッションのみ）
        embedded_errors = {}
        if self.embedded_errors_csv.exists():
            with open(self.embedded_errors_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["session_id"] == session_id and row["paper_id"] == paper_id:
                        error_id = row["error_id"]
                        embedded_errors[error_id] = {
                            "checklist_item": row["checklist_item"],
                            "before": row["before"],
                            "after": row["after"],
                            "detected_iteration": 0,  # 0 = 未検出
                            "detected": False,
                        }

        # 検出された指摘事項を取得（このセッション、フェーズ、current_iterationまで）
        if self.detected_issues_csv.exists():
            with open(self.detected_issues_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (
                        row["session_id"] == session_id
                        and row["paper_id"] == paper_id
                        and row["phase"] == phase
                        and int(row["iteration"]) <= current_iteration
                        and row["user_action"] == "accept"  # acceptされた指摘のみ
                    ):
                        detected_before = row["before"]
                        detected_after = row["after"]
                        iteration_num = int(row["iteration"])

                        # 埋め込まれた誤りとマッチング（before/afterの類似性で判定）
                        for error_id, error_info in embedded_errors.items():
                            if not error_info["detected"]:
                                # 単純な文字列マッチング（実際にはより高度なマッチングが必要かも）
                                if (
                                    error_info["before"].strip() in detected_before.strip()
                                    or detected_before.strip() in error_info["before"].strip()
                                ):
                                    embedded_errors[error_id]["detected"] = True
                                    embedded_errors[error_id]["detected_iteration"] = iteration_num

        # 検出率を計算
        total_embedded = len(embedded_errors)
        total_detected = sum(1 for e in embedded_errors.values() if e["detected"])
        detection_rate = (total_detected / total_embedded * 100) if total_embedded > 0 else 0.0

        # チェックリスト項目ごとの検出情報を整理
        items_detection = {}
        for error_id, error_info in embedded_errors.items():
            item = error_info["checklist_item"]
            if item not in items_detection:
                items_detection[item] = {
                    "detected_count": 0,
                    "total_count": 0,
                    "first_detected_iteration": 0,
                }

            items_detection[item]["total_count"] += 1
            if error_info["detected"]:
                items_detection[item]["detected_count"] += 1
                # 最初に検出されたイテレーションを記録
                if (
                    items_detection[item]["first_detected_iteration"] == 0
                    or error_info["detected_iteration"] < items_detection[item]["first_detected_iteration"]
                ):
                    items_detection[item]["first_detected_iteration"] = error_info["detected_iteration"]

        return {
            "total_embedded": total_embedded,
            "total_detected": total_detected,
            "detection_rate": detection_rate,
            "items_detection": items_detection,
            "embedded_errors": embedded_errors,  # 詳細情報も返す
        }

    def get_embedded_errors(self, paper_id: str) -> List[Dict[str, Any]]:
        """指定された論文の埋め込まれた誤りを取得"""
        errors = []
        if not self.embedded_errors_csv.exists():
            return errors

        with open(self.embedded_errors_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["paper_id"] == paper_id:
                    errors.append(row)

        return errors

    def save_response(
        self, paper_id: str, phase: str, iteration: int, response: str
    ):
        """LLMの応答を保存"""
        logs_dir = self.results_dir.parent / "logs" / paper_id
        logs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{phase}_iteration_{iteration}_response.txt"
        filepath = logs_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response)

    def save_prompt(
        self, paper_id: str, phase: str, iteration: int, prompt: str
    ):
        """LLMに送信したプロンプトを保存"""
        logs_dir = self.results_dir.parent / "logs" / paper_id
        logs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{phase}_iteration_{iteration}_prompt.txt"
        filepath = logs_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prompt)

    def calculate_detection_rate(self, paper_id: str) -> Dict[str, Any]:
        """検出率を計算"""
        embedded_errors = self.get_embedded_errors(paper_id)
        total_embedded = len(embedded_errors)

        # 検出された誤りをカウント
        # TODO: 実際の検出ロジックを実装
        # ここでは仮の実装
        total_detected = 0

        detection_rate = (
            (total_detected / total_embedded * 100) if total_embedded > 0 else 0.0
        )

        return {
            "total_embedded": total_embedded,
            "total_detected": total_detected,
            "detection_rate": detection_rate,
        }

    def save_progress(
        self,
        paper_id: str,
        phase: str,
        session_id: str,
        iteration: int,
        excluded_items: List[str],
    ):
        """進捗情報を保存"""
        # 既存の進捗データを読み込む
        progress_data = self._safe_load_json(self.progress_file, default={})

        # 論文IDのエントリがなければ作成
        if paper_id not in progress_data:
            progress_data[paper_id] = {}

        # 進捗情報を更新
        progress_data[paper_id][phase] = {
            "session_id": session_id,
            "iteration": iteration,
            "excluded_items": excluded_items,
            "last_updated": datetime.now().isoformat(),
        }

        # ファイルに保存
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

    def load_progress(
        self,
        paper_id: str,
        phase: str,
    ) -> Tuple[str, int, List[str]]:
        """進捗情報を読み込む

        Returns:
            (session_id, iteration, excluded_items): セッションID、次に開始すべきイテレーション番号と除外項目リスト
                                                    進捗がない場合は ("", 0, [])
        """
        progress_data = self._safe_load_json(self.progress_file, default={})

        # 進捗情報を取得
        if paper_id in progress_data and phase in progress_data[paper_id]:
            saved_progress = progress_data[paper_id][phase]
            session_id = saved_progress.get("session_id", "")
            iteration = saved_progress.get("iteration", 0)
            excluded_items = saved_progress.get("excluded_items", [])
            return (session_id, iteration, excluded_items)

        return ("", 0, [])

    def clear_progress(self, paper_id: str, phase: str):
        """進捗情報をクリア（フェーズ完了時）"""
        progress_data = self._safe_load_json(self.progress_file, default={})

        # 該当のフェーズ進捗を削除
        if paper_id in progress_data and phase in progress_data[paper_id]:
            del progress_data[paper_id][phase]

            # 論文の全フェーズが完了している場合、論文エントリも削除
            if not progress_data[paper_id]:
                del progress_data[paper_id]

        # ファイルに保存
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

    def generate_session_id(self) -> str:
        """新しいセッションIDを生成"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_session_metadata(
        self,
        session_id: str,
        paper_id: str,
        phase1_start: str,
        phase1_end: str = "",
        phase2_end: str = "",
        phase3_end: str = "",
    ):
        """セッションメタデータを保存"""
        sessions_data = self._safe_load_json(self.sessions_file, default={})

        if session_id not in sessions_data:
            sessions_data[session_id] = {}

        sessions_data[session_id][paper_id] = {
            "phase1_start": phase1_start,
            "phase1_end": phase1_end,
            "phase2_end": phase2_end,
            "phase3_end": phase3_end,
        }

        with open(self.sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)

    def get_excluded_items(self, paper_id: str, session_id: str = "") -> List[str]:
        """指定された論文（およびセッション）の除外項目リストを取得

        Args:
            paper_id: 論文ID
            session_id: セッションID（指定しない場合は最新の除外項目を取得）
        """
        excluded = []
        if not self.excluded_items_csv.exists():
            return excluded

        with open(self.excluded_items_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["paper_id"] == paper_id:
                    # session_idが指定されていない、または一致する場合に追加
                    if not session_id or row.get("session_id", "") == session_id:
                        excluded.append(row["checklist_item"])

        return excluded

    def get_latest_session_id(self, paper_id: str) -> str:
        """指定された論文の最新セッションIDを取得"""
        sessions_data = self._safe_load_json(self.sessions_file, default={})

        # 最新のセッションIDを見つける
        latest_session_id = ""
        for session_id, papers in sessions_data.items():
            if paper_id in papers:
                if session_id > latest_session_id:  # タイムスタンプ順
                    latest_session_id = session_id

        return latest_session_id

    # ====================================================================
    # Phase1セッション管理メソッド
    # ====================================================================

    def generate_phase1_id(self) -> str:
        """新しいPhase1 IDを生成（タイムスタンプベース）"""
        return f"phase1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def save_phase1_session(
        self,
        phase1_id: str,
        paper_id: str,
        started_at: str,
        status: str = "in_progress",
    ):
        """Phase1セッション情報を保存

        Args:
            phase1_id: Phase1セッションID
            paper_id: 論文ID
            started_at: 開始時刻（ISO形式）
            status: ステータス（"in_progress", "completed", "aborted"）
        """
        sessions_data = self._safe_load_json(self.phase1_sessions_file, default={})

        sessions_data[phase1_id] = {
            "paper_id": paper_id,
            "started_at": started_at,
            "completed_at": "",
            "iterations": 0,
            "excluded_items": [],
            "status": status,
            "final_pdf_path": "",
        }

        with open(self.phase1_sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)

    def update_phase1_session(
        self,
        phase1_id: str,
        completed_at: str = "",
        iterations: int = 0,
        excluded_items: List[str] = None,
        status: str = "",
        final_pdf_path: str = "",
    ):
        """Phase1セッション情報を更新

        Args:
            phase1_id: Phase1セッションID
            completed_at: 完了時刻（ISO形式）
            iterations: イテレーション数
            excluded_items: 除外項目リスト
            status: ステータス
            final_pdf_path: 最終PDFファイルのパス
        """
        sessions_data = self._safe_load_json(self.phase1_sessions_file, default={})

        if phase1_id not in sessions_data:
            print(f"Warning: Phase1 session {phase1_id} not found")
            return

        # 指定された項目のみ更新
        if completed_at:
            sessions_data[phase1_id]["completed_at"] = completed_at
        if iterations > 0:
            sessions_data[phase1_id]["iterations"] = iterations
        if excluded_items is not None:
            sessions_data[phase1_id]["excluded_items"] = excluded_items
        if status:
            sessions_data[phase1_id]["status"] = status
        if final_pdf_path:
            sessions_data[phase1_id]["final_pdf_path"] = final_pdf_path

        with open(self.phase1_sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)

    def get_phase1_sessions(self, paper_id: str) -> List[Dict[str, Any]]:
        """指定された論文のPhase1セッションリストを取得

        Args:
            paper_id: 論文ID

        Returns:
            Phase1セッションのリスト（新しい順）
        """
        sessions_data = self._safe_load_json(self.phase1_sessions_file, default={})

        # 指定された論文のセッションのみ抽出
        paper_sessions = []
        for phase1_id, session_info in sessions_data.items():
            if session_info["paper_id"] == paper_id:
                paper_sessions.append({
                    "phase1_id": phase1_id,
                    **session_info
                })

        # 開始時刻で降順ソート（新しい順）
        paper_sessions.sort(key=lambda x: x["started_at"], reverse=True)

        return paper_sessions

    def get_phase1_session(self, phase1_id: str) -> Optional[Dict[str, Any]]:
        """特定のPhase1セッション情報を取得

        Args:
            phase1_id: Phase1セッションID

        Returns:
            セッション情報、存在しない場合はNone
        """
        sessions_data = self._safe_load_json(self.phase1_sessions_file, default={})

        if phase1_id in sessions_data:
            return {
                "phase1_id": phase1_id,
                **sessions_data[phase1_id]
            }

        return None


if __name__ == "__main__":
    # テスト用コード
    print("DataManagerモジュールのテスト")

    # テスト用のデータマネージャーを作成
    test_dir = Path("test_results")
    dm = DataManager(test_dir)

    # テストデータを記録
    dm.record_embedded_error(
        paper_id="paper001",
        error_id=1,
        checklist_item="項目1.1",
        category="文法",
        before="The data is...",
        after="The data are...",
        location="Section 3, line 45",
    )

    dm.record_iteration(
        paper_id="paper001",
        phase="phase1",
        iteration=1,
        llm_model="gemini-1.5-pro",
        detected_errors=["error1", "error2"],
        new_issues_count=2,
        excluded_items=[],
    )

    print("✓ テストデータの記録成功")
    print(f"✓ CSVファイルが作成されました: {test_dir}")

    # クリーンアップ
    import shutil
    shutil.rmtree(test_dir)
    print("✓ テストディレクトリを削除しました")
