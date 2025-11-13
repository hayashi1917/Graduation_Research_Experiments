"""
論文管理モジュール
論文ファイルのバージョン管理とTeX編集
"""

import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime


class PaperManager:
    """論文ファイルを管理するクラス"""

    def __init__(self, paper_dir: Path, versions_dir: Path):
        """
        Args:
            paper_dir: 論文ファイルのディレクトリ
            versions_dir: バージョン管理用ディレクトリ
        """
        self.paper_dir = Path(paper_dir)
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def save_version(
        self,
        paper_id: str,
        phase: str,
        iteration: int,
        pdf_path: Path,
    ):
        """
        現在の論文ファイルをバージョンとして保存

        Args:
            paper_id: 論文ID
            phase: フェーズ名
            iteration: イテレーション番号
            pdf_path: PDFファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_name = f"{phase}_iter{iteration}_{timestamp}"

        version_dir = self.versions_dir / paper_id / version_name
        version_dir.mkdir(parents=True, exist_ok=True)

        # PDFファイルをコピー
        if pdf_path and pdf_path.exists():
            shutil.copy2(pdf_path, version_dir / pdf_path.name)

        print(f"✓ バージョンを保存しました: {version_dir}")


    def restore_version(
        self,
        paper_id: str,
        version_name: str,
        pdf_path: Path,
    ):
        """
        指定されたバージョンに復元

        Args:
            paper_id: 論文ID
            version_name: バージョン名
            pdf_path: 復元先のPDFファイルパス
        """
        version_dir = self.versions_dir / paper_id / version_name

        if not version_dir.exists():
            print(f"⚠ バージョンが見つかりません: {version_dir}")
            return

        # PDFファイルを復元
        version_pdf = version_dir / pdf_path.name
        if version_pdf.exists():
            shutil.copy2(version_pdf, pdf_path)
            print(f"✓ PDFファイルを復元しました")

    def list_versions(self, paper_id: str):
        """
        指定された論文の全バージョンをリスト表示

        Args:
            paper_id: 論文ID
        """
        paper_versions_dir = self.versions_dir / paper_id

        if not paper_versions_dir.exists():
            print(f"バージョンが見つかりません: {paper_id}")
            return

        versions = sorted(paper_versions_dir.iterdir())

        if not versions:
            print(f"バージョンが見つかりません: {paper_id}")
            return

        print(f"\n{paper_id} のバージョン:")
        for i, version in enumerate(versions, 1):
            print(f"  {i}. {version.name}")


if __name__ == "__main__":
    print("PaperManagerモジュールのテスト")

    # テスト用のディレクトリを作成
    test_paper_dir = Path("test_papers")
    test_versions_dir = Path("test_versions")

    test_paper_dir.mkdir(exist_ok=True)
    test_versions_dir.mkdir(exist_ok=True)

    # テスト用のPDFファイルを作成（ダミー）
    test_pdf = test_paper_dir / "test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 test")

    # PaperManagerを初期化
    pm = PaperManager(test_paper_dir, test_versions_dir)

    # バージョンを保存
    pm.save_version(
        paper_id="test001",
        phase="phase1",
        iteration=1,
        pdf_path=test_pdf,
    )

    # バージョンをリスト
    pm.list_versions("test001")

    # クリーンアップ
    import shutil
    shutil.rmtree(test_paper_dir)
    shutil.rmtree(test_versions_dir)
    print("\n✓ テスト完了")
