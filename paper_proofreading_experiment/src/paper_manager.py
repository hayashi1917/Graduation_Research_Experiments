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
        tex_path: Path,
        pdf_path: Optional[Path] = None,
    ):
        """
        現在の論文ファイルをバージョンとして保存

        Args:
            paper_id: 論文ID
            phase: フェーズ名
            iteration: イテレーション番号
            tex_path: TeXファイルのパス
            pdf_path: PDFファイルのパス（オプション）
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_name = f"{phase}_iter{iteration}_{timestamp}"

        version_dir = self.versions_dir / paper_id / version_name
        version_dir.mkdir(parents=True, exist_ok=True)

        # TeXファイルをコピー
        if tex_path.exists():
            shutil.copy2(tex_path, version_dir / tex_path.name)

        # PDFファイルをコピー（存在する場合）
        if pdf_path and pdf_path.exists():
            shutil.copy2(pdf_path, version_dir / pdf_path.name)

        print(f"✓ バージョンを保存しました: {version_dir}")

    def apply_correction(
        self,
        tex_path: Path,
        before_text: str,
        after_text: str,
        backup: bool = True,
    ) -> bool:
        """
        TeXファイルに修正を適用

        Args:
            tex_path: TeXファイルのパス
            before_text: 修正前のテキスト
            after_text: 修正後のテキスト
            backup: バックアップを作成するか

        Returns:
            修正が成功したかどうか
        """
        # ファイルを読み込む
        with open(tex_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修正前のテキストが存在するか確認
        if before_text not in content:
            print(f"⚠ 修正前のテキストが見つかりません:")
            print(f"  探しているテキスト: {before_text[:100]}...")
            return False

        # バックアップを作成
        if backup:
            backup_path = tex_path.with_suffix(".tex.bak")
            shutil.copy2(tex_path, backup_path)

        # テキストを置換
        new_content = content.replace(before_text, after_text, 1)

        # ファイルに書き込む
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✓ 修正を適用しました")
        return True

    def restore_version(
        self,
        paper_id: str,
        version_name: str,
        tex_path: Path,
        pdf_path: Optional[Path] = None,
    ):
        """
        指定されたバージョンに復元

        Args:
            paper_id: 論文ID
            version_name: バージョン名
            tex_path: 復元先のTeXファイルパス
            pdf_path: 復元先のPDFファイルパス（オプション）
        """
        version_dir = self.versions_dir / paper_id / version_name

        if not version_dir.exists():
            print(f"⚠ バージョンが見つかりません: {version_dir}")
            return

        # TeXファイルを復元
        version_tex = version_dir / tex_path.name
        if version_tex.exists():
            shutil.copy2(version_tex, tex_path)
            print(f"✓ TeXファイルを復元しました")

        # PDFファイルを復元（存在する場合）
        if pdf_path:
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

    # テスト用のTeXファイルを作成
    test_tex = test_paper_dir / "test.tex"
    test_tex.write_text("The data is analyzed.")

    # PaperManagerを初期化
    pm = PaperManager(test_paper_dir, test_versions_dir)

    # バージョンを保存
    pm.save_version(
        paper_id="test001",
        phase="phase1",
        iteration=1,
        tex_path=test_tex,
    )

    # 修正を適用
    pm.apply_correction(
        tex_path=test_tex,
        before_text="The data is analyzed.",
        after_text="The data are analyzed.",
    )

    print(f"\n修正後の内容: {test_tex.read_text()}")

    # バージョンをリスト
    pm.list_versions("test001")

    # クリーンアップ
    import shutil
    shutil.rmtree(test_paper_dir)
    shutil.rmtree(test_versions_dir)
    print("\n✓ テスト完了")
