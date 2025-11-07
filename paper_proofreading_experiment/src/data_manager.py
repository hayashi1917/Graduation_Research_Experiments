"""
データ管理モジュール
実験データをCSVファイルに記録する
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


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

        # CSVファイルを初期化
        self._initialize_csv_files()

    def _initialize_csv_files(self):
        """CSVファイルを初期化（ヘッダー行を作成）"""

        # embedded_errors.csv
        if not self.embedded_errors_csv.exists():
            with open(self.embedded_errors_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
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
                    "paper_id",
                    "total_embedded",
                    "total_detected",
                    "detection_rate",
                    "phase1_iterations",
                    "phase3_iterations",
                    "excluded_items_count",
                    "completion_time",
                ])

    def record_embedded_error(
        self,
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
                paper_id,
                checklist_item,
                reason,
                timestamp,
                example_case,
            ])

    def record_summary(
        self,
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
                paper_id,
                total_embedded,
                total_detected,
                detection_rate,
                phase1_iterations,
                phase3_iterations,
                excluded_items_count,
                completion_time,
            ])

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

    def get_excluded_items(self, paper_id: str) -> List[str]:
        """指定された論文の除外項目リストを取得"""
        excluded = []
        if not self.excluded_items_csv.exists():
            return excluded

        with open(self.excluded_items_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["paper_id"] == paper_id:
                    excluded.append(row["checklist_item"])

        return excluded

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
