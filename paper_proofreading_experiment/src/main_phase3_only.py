#!/usr/bin/env python3
"""フェーズ3の機能だけを提供する簡易CLI。"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict

import yaml

from data_manager import DataManager
from llm_client import create_llm_client
from paper_manager import PaperManager
from phase3_proofreader import Phase3Proofreader


def load_config(config_dir: Path) -> Dict[str, dict]:
    settings_path = config_dir / "settings.yaml"
    prompts_path = config_dir / "prompts.yaml"

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    with open(prompts_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    return {"settings": settings, "prompts": prompts}


def load_checklist(base_dir: Path, checklist_file: str) -> str:
    checklist_path = base_dir / checklist_file
    with open(checklist_path, "r", encoding="utf-8") as f:
        return f.read()


def prompt_file_path(message: str, expected_suffix: str) -> Path:
    while True:
        raw = input(message).strip()
        if not raw:
            print("入力が空です。もう一度入力してください。")
            continue

        path = Path(raw).expanduser()
        if not path.exists():
            print(f"ファイルが見つかりません: {path}")
            continue

        if not path.is_file():
            print("ファイルではありません。")
            continue

        if expected_suffix and path.suffix.lower() != expected_suffix:
            print(f"{expected_suffix} ファイルを指定してください。")
            continue

        return path


def build_iteration_file_getter() -> Callable[[int], Dict[str, Path]]:
    def getter(iteration: int) -> Dict[str, Path]:
        print("\n" + "-" * 60)
        print(f"イテレーション {iteration} の入力ファイルを指定してください。")
        tex_path = prompt_file_path("TeXファイルのパス (.tex): ", ".tex")
        pdf_path = prompt_file_path("PDFファイルのパス (.pdf): ", ".pdf")
        return {"tex_path": tex_path, "pdf_path": pdf_path}

    return getter


def main():
    parser = argparse.ArgumentParser(description="フェーズ3専用の簡易CLI")
    parser.add_argument("--paper-id", required=True, help="論文ID")
    parser.add_argument("--config-dir", default="config", help="設定ディレクトリ")
    parser.add_argument("--results-dir", default="data/results", help="結果保存ディレクトリ")
    parser.add_argument("--versions-dir", default="data/versions", help="バージョン保存ディレクトリ")
    parser.add_argument("--max-iterations", type=int, default=None, help="最大イテレーション数")

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    config_dir = base_dir / args.config_dir
    results_dir = base_dir / args.results_dir
    versions_dir = base_dir / args.versions_dir

    config = load_config(config_dir)
    settings = config["settings"]
    prompts = config["prompts"]
    checklist = load_checklist(base_dir, settings["checklist_file"])

    llm_client = create_llm_client(
        provider=settings["llm"]["proofreading"]["provider"],
        model=settings["llm"]["proofreading"]["model"],
        api_key_env=settings["llm"]["proofreading"]["api_key_env"],
        temperature=settings["llm"]["proofreading"]["temperature"],
    )

    data_manager = DataManager(results_dir)
    paper_manager = PaperManager(base_dir / settings["paths"]["papers"], versions_dir)

    max_iterations = args.max_iterations or settings["experiment"]["max_iterations"]

    print("\n" + "=" * 70)
    print("フェーズ3簡易モード")
    print("=" * 70)
    print(f"論文ID: {args.paper_id}")
    print(f"最大イテレーション数: {max_iterations}")
    print("TeXとPDFファイルを各イテレーション毎に指定してください。")
    print("=" * 70 + "\n")

    proofreader = Phase3Proofreader(
        llm_client=llm_client,
        data_manager=data_manager,
        paper_manager=paper_manager,
        prompt_template=prompts["prompt_a_and_c"]["template"],
        checklist=checklist,
        max_iterations=max_iterations,
    )

    start_time = datetime.now()
    result = proofreader.run(
        paper_id=args.paper_id,
        pdf_path=None,
        iteration_file_getter=build_iteration_file_getter(),
    )

    end_time = datetime.now()
    print("\nフェーズ3簡易モード完了")
    print(f"検出された誤り数: {result['detected_count']}")
    print(f"総イテレーション数: {result['iterations']}")
    print(f"経過時間: {end_time - start_time}")
if __name__ == "__main__":
    main()
