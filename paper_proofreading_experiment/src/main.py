#!/usr/bin/env python3
"""
学術論文形式校正実験 - メインプログラム

使用方法:
    python main.py --paper-id paper001 --phase 1
    python main.py --paper-id paper001 --phase 2
    python main.py --paper-id paper001 --phase 3
"""

import argparse
import sys
import yaml
from pathlib import Path
from datetime import datetime

# 自作モジュールをインポート
from llm_client import create_llm_client
from data_manager import DataManager
from paper_manager import PaperManager
from phase1_cleaner import Phase1Cleaner
from phase2_embedder import Phase2Embedder
from phase3_proofreader import Phase3Proofreader


def load_config(config_dir: Path) -> dict:
    """設定ファイルを読み込む"""
    settings_path = config_dir / "settings.yaml"
    prompts_path = config_dir / "prompts.yaml"

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    with open(prompts_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    return {
        "settings": settings,
        "prompts": prompts,
    }


def load_checklist(config_dir: Path, filename: str) -> str:
    """チェックリストを読み込む"""
    checklist_path = config_dir / filename
    with open(checklist_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="学術論文形式校正実験プログラム"
    )
    parser.add_argument(
        "--paper-id",
        required=True,
        help="論文ID（例: paper001）",
    )
    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        choices=[1, 2, 3],
        help="実行フェーズ（1: クリーン化, 2: 誤り埋め込み, 3: 校正実験）",
    )
    parser.add_argument(
        "--config-dir",
        default="config",
        help="設定ファイルのディレクトリ（デフォルト: config）",
    )
    parser.add_argument(
        "--paper-dir",
        default="data/papers",
        help="論文ファイルのディレクトリ（デフォルト: data/papers）",
    )

    args = parser.parse_args()

    # パスを設定
    base_dir = Path(__file__).parent.parent
    config_dir = base_dir / args.config_dir
    paper_dir = base_dir / args.paper_dir / args.paper_id
    results_dir = base_dir / "data" / "results"

    # 論文ファイルのパスを確認
    pdf_path = paper_dir / f"{args.paper_id}.pdf"
    tex_path = paper_dir / f"{args.paper_id}.tex"

    if not pdf_path.exists() or not tex_path.exists():
        print(f"エラー: 論文ファイルが見つかりません。")
        print(f"  PDF: {pdf_path}")
        print(f"  TeX: {tex_path}")
        print(f"\n以下のディレクトリ構造を確認してください:")
        print(f"  {paper_dir}/")
        print(f"    ├── {args.paper_id}.pdf")
        print(f"    └── {args.paper_id}.tex")
        sys.exit(1)

    # 設定を読み込む
    config = load_config(config_dir)
    settings = config["settings"]
    prompts = config["prompts"]

    # チェックリストを読み込む
    checklist = load_checklist(config_dir, settings["checklist_file"].split("/")[-1])

    # データマネージャーを初期化
    data_manager = DataManager(results_dir)

    # 論文マネージャーを初期化
    versions_dir = base_dir / "data" / "versions"
    paper_manager = PaperManager(paper_dir, versions_dir)

    # 実験開始時刻を記録
    start_time = datetime.now()

    print(f"\n{'='*70}")
    print(f"学術論文形式校正実験")
    print(f"{'='*70}")
    print(f"論文ID: {args.paper_id}")
    print(f"フェーズ: {args.phase}")
    print(f"開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # フェーズごとの処理
    if args.phase == 1:
        # フェーズ1: クリーン化
        print("フェーズ1: クリーン化")

        # Geminiクライアントを作成
        llm_client = create_llm_client(
            provider=settings["llm"]["proofreading"]["provider"],
            model=settings["llm"]["proofreading"]["model"],
            api_key_env=settings["llm"]["proofreading"]["api_key_env"],
            temperature=settings["llm"]["proofreading"]["temperature"],
        )

        # クリーナーを作成
        cleaner = Phase1Cleaner(
            llm_client=llm_client,
            data_manager=data_manager,
            paper_manager=paper_manager,
            prompt_template=prompts["prompt_a_and_c"]["template"],
            checklist=checklist,
            max_iterations=settings["experiment"]["max_iterations"],
        )

        # クリーン化を実行
        result = cleaner.run(
            paper_id=args.paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
        )

        print(f"\nフェーズ1完了:")
        print(f"  反復回数: {result['iterations']}")
        print(f"  除外された項目数: {result['excluded_items_count']}")
        print(f"  停止理由: {result['stopped_reason']}")

    elif args.phase == 2:
        # フェーズ2: 誤り埋め込み
        print("フェーズ2: 誤り埋め込み")

        # Claudeクライアントを作成
        llm_client = create_llm_client(
            provider=settings["llm"]["embedding"]["provider"],
            model=settings["llm"]["embedding"]["model"],
            api_key_env=settings["llm"]["embedding"]["api_key_env"],
            temperature=settings["llm"]["embedding"]["temperature"],
        )

        # 除外項目を取得（フェーズ1で除外された項目があれば）
        excluded_items = data_manager.get_excluded_items(args.paper_id)

        # エンベッダーを作成
        embedder = Phase2Embedder(
            llm_client=llm_client,
            data_manager=data_manager,
            prompt_template=prompts["prompt_b"]["template"],
            checklist=checklist,
            num_errors=settings["experiment"]["num_errors"],
            excluded_items=excluded_items,
        )

        # 誤り埋め込みを実行
        result = embedder.run(
            paper_id=args.paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
        )

        print(f"\nフェーズ2完了:")
        print(f"  埋め込まれた誤り数: {result['count']}")
        print(f"  成功: {result['success']}")

    elif args.phase == 3:
        # フェーズ3: 校正実験
        print("フェーズ3: 校正実験")

        # Geminiクライアントを作成
        llm_client = create_llm_client(
            provider=settings["llm"]["proofreading"]["provider"],
            model=settings["llm"]["proofreading"]["model"],
            api_key_env=settings["llm"]["proofreading"]["api_key_env"],
            temperature=settings["llm"]["proofreading"]["temperature"],
        )

        # プルーフリーダーを作成
        proofreader = Phase3Proofreader(
            llm_client=llm_client,
            data_manager=data_manager,
            paper_manager=paper_manager,
            prompt_template=prompts["prompt_a_and_c"]["template"],
            checklist=checklist,
            max_iterations=settings["experiment"]["max_iterations"],
        )

        # 校正実験を実行
        result = proofreader.run(
            paper_id=args.paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
        )

        print(f"\nフェーズ3完了:")
        print(f"  反復回数: {result['iterations']}")
        print(f"  検出された誤り数: {result['detected_count']}")
        print(f"  除外された項目数: {result['excluded_items_count']}")
        print(f"  停止理由: {result['stopped_reason']}")

        # サマリーを記録
        embedded_errors = data_manager.get_embedded_errors(args.paper_id)
        total_embedded = len(embedded_errors)
        detection_rate = (
            (result['detected_count'] / total_embedded * 100)
            if total_embedded > 0 else 0.0
        )

        # フェーズ1の反復回数を取得（TODO: 実装）
        phase1_iterations = 0

        completion_time = datetime.now() - start_time

        data_manager.record_summary(
            paper_id=args.paper_id,
            total_embedded=total_embedded,
            total_detected=result['detected_count'],
            detection_rate=detection_rate,
            phase1_iterations=phase1_iterations,
            phase3_iterations=result['iterations'],
            excluded_items_count=result['excluded_items_count'],
            completion_time=str(completion_time),
        )

    # 実験終了
    end_time = datetime.now()
    elapsed_time = end_time - start_time

    print(f"\n{'='*70}")
    print(f"実験完了")
    print(f"終了時刻: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"経過時間: {elapsed_time}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
