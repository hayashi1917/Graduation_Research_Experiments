"""
FastAPI バックエンド - 論文校正実験用Web UI
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import shutil
from datetime import datetime

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient, GeminiClient, ClaudeClient
from data_manager import DataManager
from response_parser import ResponseParser
from paper_manager import PaperManager
from websocket_adapters import WebSocketPhase1Adapter, WebSocketPhase2Adapter, WebSocketPhase3Adapter

import yaml


# FastAPIアプリケーションの初期化
app = FastAPI(title="Paper Proofreading Experiment API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの提供（フロントエンド）
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# WebSocket接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.phase_adapters: Dict[str, any] = {}  # 実行中のアダプター

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.phase_adapters:
            del self.phase_adapters[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    def set_adapter(self, client_id: str, adapter):
        self.phase_adapters[client_id] = adapter

    def get_adapter(self, client_id: str):
        return self.phase_adapters.get(client_id)

manager = ConnectionManager()

# 設定とデータマネージャーの初期化
config_dir = Path(__file__).parent.parent / "config"
data_dir = Path(__file__).parent.parent / "data"
papers_dir = Path(__file__).parent.parent / "papers"

# ディレクトリ作成
papers_dir.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)

# 結果とバージョンディレクトリ
results_dir = data_dir / "results"
versions_dir = data_dir / "versions"
logs_dir = data_dir / "logs"
phase3_only_dir = data_dir / "phase3_only"

results_dir.mkdir(parents=True, exist_ok=True)
versions_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)
phase3_only_dir.mkdir(parents=True, exist_ok=True)

settings = yaml.safe_load((config_dir / "settings.yaml").read_text(encoding="utf-8"))
prompts = yaml.safe_load((config_dir / "prompts.yaml").read_text(encoding="utf-8"))
checklist = (config_dir / "checklist.md").read_text(encoding="utf-8")

# 正しい引数でマネージャーを初期化
data_manager = DataManager(results_dir=results_dir)
paper_manager = PaperManager(paper_dir=papers_dir, versions_dir=versions_dir)


@app.get("/")
async def read_root():
    """フロントエンドのindex.htmlを返す"""
    return FileResponse(frontend_path / "index.html")


@app.get("/phase3-only")
async def read_phase3_only():
    """フェーズ3簡易UIを返す"""
    page_path = frontend_path / "phase3_only.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="phase3_only.html が見つかりません")
    return FileResponse(page_path)


def _phase3_manifest_path(paper_id: str) -> Path:
    return phase3_only_dir / paper_id / "manifest.json"


def _load_phase3_manifest(paper_id: str) -> dict:
    manifest_path = _phase3_manifest_path(paper_id)
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"paper_id": paper_id, "iterations": []}


def _save_phase3_manifest(paper_id: str, manifest: dict):
    manifest_path = _phase3_manifest_path(paper_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/phase3-only/iterations/{paper_id}")
async def list_phase3_iterations(paper_id: str):
    """フェーズ3簡易モードのアップロード履歴を取得"""
    manifest = _load_phase3_manifest(paper_id)
    iterations = sorted(manifest.get("iterations", []), key=lambda item: item.get("iteration", 0))
    next_iteration = iterations[-1]["iteration"] + 1 if iterations else 1
    return {
        "paper_id": paper_id,
        "iterations": iterations,
        "next_iteration": next_iteration,
    }


@app.post("/api/phase3-only/iterations")
async def upload_phase3_iteration(
    paper_id: str = Form(...),
    iteration: int = Form(...),
    tex_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
):
    """各イテレーションのTeX/PDFをアップロード"""

    if iteration < 1:
        raise HTTPException(status_code=400, detail="iteration は1以上にしてください")

    session_dir = phase3_only_dir / paper_id
    iteration_dir = session_dir / f"iteration_{iteration:02d}"

    if iteration_dir.exists():
        shutil.rmtree(iteration_dir)
    iteration_dir.mkdir(parents=True, exist_ok=True)

    tex_filename = Path(tex_file.filename or f"iteration_{iteration}.tex").name
    pdf_filename = Path(pdf_file.filename or f"iteration_{iteration}.pdf").name

    tex_path = iteration_dir / tex_filename
    pdf_path = iteration_dir / pdf_filename

    with open(tex_path, "wb") as tex_out:
        tex_out.write(await tex_file.read())

    with open(pdf_path, "wb") as pdf_out:
        pdf_out.write(await pdf_file.read())

    uploaded_at = datetime.utcnow().isoformat()

    manifest = _load_phase3_manifest(paper_id)
    entries = [entry for entry in manifest.get("iterations", []) if entry.get("iteration") != iteration]
    entry = {
        "iteration": iteration,
        "tex_filename": tex_filename,
        "pdf_filename": pdf_filename,
        "tex_url": f"/api/phase3-only/files/{paper_id}/{iteration:02d}/{tex_filename}",
        "pdf_url": f"/api/phase3-only/files/{paper_id}/{iteration:02d}/{pdf_filename}",
        "uploaded_at": uploaded_at,
    }
    entries.append(entry)
    manifest["iterations"] = entries
    _save_phase3_manifest(paper_id, manifest)

    return {
        "status": "success",
        "message": f"イテレーション{iteration}のファイルを保存しました",
        "entry": entry,
    }


@app.delete("/api/phase3-only/iterations/{paper_id}")
async def reset_phase3_iterations(paper_id: str):
    """アップロード済みのイテレーションを削除"""
    session_dir = phase3_only_dir / paper_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    return {"status": "success", "message": "アップロード済みのファイルを削除しました"}


@app.get("/api/phase3-only/files/{paper_id}/{iteration}/{filename}")
async def download_phase3_file(paper_id: str, iteration: str, filename: str):
    """アップロード済みファイルをダウンロード"""
    safe_name = Path(filename).name
    iteration_dir = phase3_only_dir / paper_id / f"iteration_{iteration}"
    file_path = iteration_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    return FileResponse(file_path)


@app.get("/api/papers")
async def get_papers():
    """登録されている論文のリストを取得"""
    papers = []
    if papers_dir.exists():
        for paper_dir in papers_dir.iterdir():
            if paper_dir.is_dir():
                pdf_files = list(paper_dir.glob("*.pdf"))
                if pdf_files:
                    papers.append({
                        "id": paper_dir.name,
                        "pdf": pdf_files[0].name,
                    })
    return {"papers": papers}


@app.post("/api/papers/upload")
async def upload_paper(
    paper_id: str = Form(...),
    pdf_file: UploadFile = File(...),
):
    """論文をアップロード"""
    try:
        # 論文ディレクトリを作成
        paper_dir = papers_dir / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)

        # PDFファイルを保存
        pdf_path = paper_dir / pdf_file.filename
        with open(pdf_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)

        return {
            "status": "success",
            "message": f"論文 {paper_id} をアップロードしました",
            "pdf": pdf_file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """設定を取得"""
    return {
        "settings": settings,
        "checklist": checklist,
    }


@app.post("/api/config/settings")
async def update_settings(new_settings: dict):
    """設定を更新"""
    try:
        global settings
        settings.update(new_settings)

        # 設定ファイルに保存
        with open(config_dir / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True)

        return {"status": "success", "message": "設定を更新しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/{paper_id}")
async def get_logs(paper_id: str, phase: Optional[str] = None):
    """ログを取得"""
    try:
        logs_dir = data_dir / "logs" / paper_id
        if not logs_dir.exists():
            return {"logs": []}

        logs = []
        for log_file in sorted(logs_dir.glob("*.txt")):
            if phase and phase not in log_file.name:
                continue
            logs.append({
                "filename": log_file.name,
                "content": log_file.read_text(encoding="utf-8"),
                "timestamp": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
            })

        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/iterations/{paper_id}")
async def get_iterations(paper_id: str):
    """イテレーション履歴を取得"""
    try:
        csv_path = results_dir / "iteration_log.csv"
        if not csv_path.exists():
            return {"iterations": []}

        import csv
        iterations = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["paper_id"] == paper_id:
                    iterations.append(row)

        return {"iterations": iterations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{paper_id}")
async def get_sessions(paper_id: str):
    """指定された論文のセッション一覧を取得"""
    try:
        sessions_file = results_dir / "sessions.json"
        if not sessions_file.exists():
            return {"sessions": []}

        with open(sessions_file, "r", encoding="utf-8") as f:
            sessions_data = json.load(f)

        # この論文に関連するセッションを抽出
        paper_sessions = []
        for session_id, papers in sessions_data.items():
            if paper_id in papers:
                session_info = papers[paper_id]
                paper_sessions.append({
                    "session_id": session_id,
                    "phase1_start": session_info.get("phase1_start", ""),
                    "phase1_end": session_info.get("phase1_end", ""),
                    "phase2_end": session_info.get("phase2_end", ""),
                    "phase3_end": session_info.get("phase3_end", ""),
                    "phase1_complete": bool(session_info.get("phase1_end")),
                    "phase2_complete": bool(session_info.get("phase2_end")),
                    "phase3_complete": bool(session_info.get("phase3_end")),
                })

        # 新しい順にソート
        paper_sessions.sort(key=lambda x: x["session_id"], reverse=True)

        return {"sessions": paper_sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/detection_rates/{paper_id}/{session_id}")
async def get_detection_rates(paper_id: str, session_id: str):
    """指定されたセッションの検出率を取得"""
    try:
        # Phase3の最終イテレーション番号を取得
        csv_path = results_dir / "iteration_log.csv"
        max_iteration = 0

        if csv_path.exists():
            import csv
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row["session_id"] == session_id and
                        row["paper_id"] == paper_id and
                        row["phase"] == "phase3"):
                        max_iteration = max(max_iteration, int(row["iteration"]))

        if max_iteration == 0:
            return {
                "total_embedded": 0,
                "total_detected": 0,
                "detection_rate": 0.0,
                "items_detection": {},
            }

        # 検出率を計算
        detection_data = data_manager.calculate_detection_rates(
            session_id=session_id,
            paper_id=paper_id,
            phase="phase3",
            current_iteration=max_iteration
        )

        return detection_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続"""
    # クライアントIDを生成
    client_id = f"client_{id(websocket)}"

    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()

            # クライアントからのメッセージを処理
            if data.get("type") == "action":
                # ユーザーの判断を受信
                action = data.get("action")
                payload = data.get("payload")

                # 実行中のアダプターにアクションを通知
                adapter = manager.get_adapter(client_id)
                if adapter:
                    adapter.set_user_action(action, payload)

                await manager.send_message({
                    "type": "action_received",
                    "action": action,
                }, client_id)

            elif data.get("type") == "start_phase":
                # フェーズ実行を開始
                paper_id = data.get("paper_id")
                phase = data.get("phase")

                # バックグラウンドで実行
                asyncio.create_task(execute_phase(paper_id, phase, websocket, client_id))

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocketエラー: {e}")
        manager.disconnect(client_id)


async def execute_phase(paper_id: str, phase: str, websocket: WebSocket, client_id: str):
    """フェーズを実行（バックグラウンドタスク）"""
    try:
        # 論文ファイルのパスを取得
        paper_dir = papers_dir / paper_id
        pdf_files = list(paper_dir.glob("*.pdf"))

        if not pdf_files:
            await manager.send_message({
                "type": "error",
                "message": "論文ファイルが見つかりません",
            }, client_id)
            return

        pdf_path = pdf_files[0]

        # LLMクライアントの初期化
        if phase in ["phase1", "phase3"]:
            llm_config = settings["llm"]["proofreading"]
        else:  # phase2
            llm_config = settings["llm"]["embedding"]

        # APIキーを環境変数から取得
        provider = llm_config["provider"]
        model = llm_config["model"]
        temperature = llm_config.get("temperature", 0.0)

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("環境変数 GEMINI_API_KEY が設定されていません")
            llm_client = GeminiClient(model=model, api_key=api_key, temperature=temperature)
        elif provider in ["anthropic", "claude"]:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("環境変数 ANTHROPIC_API_KEY が設定されていません")
            llm_client = ClaudeClient(model=model, api_key=api_key, temperature=temperature)
        else:
            raise ValueError(f"未対応のプロバイダー: {provider}")

        # フェーズ実行
        if phase == "phase1":
            await execute_phase1(paper_id, pdf_path, llm_client, websocket, client_id)
        elif phase == "phase2":
            await execute_phase2(paper_id, pdf_path, llm_client, websocket, client_id)
        elif phase == "phase3":
            await execute_phase3(paper_id, pdf_path, llm_client, websocket, client_id)

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        await manager.send_message({
            "type": "error",
            "message": error_msg,
        }, client_id)


async def execute_phase1(
    paper_id: str,
    pdf_path: Path,
    llm_client: LLMClient,
    websocket: WebSocket,
    client_id: str
):
    """フェーズ1を実行"""
    try:
        await manager.send_message({
            "type": "phase_start",
            "phase": "phase1",
            "message": "フェーズ1: クリーン化を開始",
        }, client_id)

        # WebSocketアダプターを作成
        adapter = WebSocketPhase1Adapter(
            llm_client=llm_client,
            data_manager=data_manager,
            paper_manager=paper_manager,
            prompt_template=prompts["prompt_a_and_c"]["template"],
            checklist=checklist,
            versions_dir=versions_dir,
        )

        # アダプターを登録
        manager.set_adapter(client_id, adapter)

        # 実行
        result = await adapter.run(
            paper_id=paper_id,
            pdf_path=pdf_path,
            websocket=websocket,
        )

        await manager.send_message({
            "type": "phase_complete",
            "phase": "phase1",
            "message": f"フェーズ1が完了しました（イテレーション: {result['iterations']}）",
            "result": result,
        }, client_id)

    except Exception as e:
        import traceback
        await manager.send_message({
            "type": "error",
            "message": f"フェーズ1実行エラー: {str(e)}\n{traceback.format_exc()}",
        }, client_id)
    finally:
        # アダプターを削除
        if client_id in manager.phase_adapters:
            del manager.phase_adapters[client_id]


async def execute_phase2(
    paper_id: str,
    pdf_path: Path,
    llm_client: LLMClient,
    websocket: WebSocket,
    client_id: str
):
    """フェーズ2を実行"""
    try:
        await manager.send_message({
            "type": "phase_start",
            "phase": "phase2",
            "message": "フェーズ2: エラー埋め込みを開始",
        }, client_id)

        # WebSocketアダプターを作成
        adapter = WebSocketPhase2Adapter(
            llm_client=llm_client,
            data_manager=data_manager,
            prompt_template=prompts["prompt_b"]["template"],
            checklist=checklist,
            num_errors=settings["experiment"]["num_errors"],
        )

        # アダプターを登録
        manager.set_adapter(client_id, adapter)

        # 実行
        result = await adapter.run(
            paper_id=paper_id,
            pdf_path=pdf_path,
            websocket=websocket,
        )

        await manager.send_message({
            "type": "phase_complete",
            "phase": "phase2",
            "message": f"フェーズ2が完了しました（埋め込まれた誤り: {result['count']}件）",
            "result": result,
        }, client_id)

    except Exception as e:
        import traceback
        await manager.send_message({
            "type": "error",
            "message": f"フェーズ2実行エラー: {str(e)}\n{traceback.format_exc()}",
        }, client_id)
    finally:
        # アダプターを削除
        if client_id in manager.phase_adapters:
            del manager.phase_adapters[client_id]


async def execute_phase3(
    paper_id: str,
    pdf_path: Path,
    llm_client: LLMClient,
    websocket: WebSocket,
    client_id: str
):
    """フェーズ3を実行"""
    try:
        await manager.send_message({
            "type": "phase_start",
            "phase": "phase3",
            "message": "フェーズ3: 校正を開始",
        }, client_id)

        # WebSocketアダプターを作成（Phase3はPhase1と同じロジック）
        adapter = WebSocketPhase3Adapter(
            llm_client=llm_client,
            data_manager=data_manager,
            paper_manager=paper_manager,
            prompt_template=prompts["prompt_a_and_c"]["template"],
            checklist=checklist,
        )

        # アダプターを登録
        manager.set_adapter(client_id, adapter)

        # 実行
        result = await adapter.run(
            paper_id=paper_id,
            pdf_path=pdf_path,
            websocket=websocket,
        )

        await manager.send_message({
            "type": "phase_complete",
            "phase": "phase3",
            "message": f"フェーズ3が完了しました（イテレーション: {result['iterations']}）",
            "result": result,
        }, client_id)

    except Exception as e:
        import traceback
        await manager.send_message({
            "type": "error",
            "message": f"フェーズ3実行エラー: {str(e)}\n{traceback.format_exc()}",
        }, client_id)
    finally:
        # アダプターを削除
        if client_id in manager.phase_adapters:
            del manager.phase_adapters[client_id]


# ====================================================================
# データ管理エンドポイント
# ====================================================================

@app.post("/api/reset")
async def reset_data(request: dict):
    """データをリセット"""
    reset_results = request.get("reset_results", False)
    reset_versions = request.get("reset_versions", False)
    reset_progress = request.get("reset_progress", False)

    deleted_items = []

    try:
        if reset_results:
            # 実験結果データを削除
            import shutil
            if results_dir.exists():
                # CSVファイルとJSONファイルを削除（ディレクトリは残す）
                for file in results_dir.glob("*.csv"):
                    file.unlink()
                    deleted_items.append(str(file.name))
                for file in results_dir.glob("*.json"):
                    file.unlink()
                    deleted_items.append(str(file.name))

                # DataManagerを再初期化してCSVヘッダーを作成
                global data_manager
                data_manager = DataManager(results_dir=results_dir)

        if reset_versions:
            # バージョン履歴を削除
            import shutil
            if versions_dir.exists():
                shutil.rmtree(versions_dir)
                versions_dir.mkdir(parents=True, exist_ok=True)
                deleted_items.append("versions/")

        if reset_progress:
            # 進捗情報を削除
            progress_file = results_dir / "progress.json"
            if progress_file.exists():
                progress_file.unlink()
                deleted_items.append("progress.json")

        return JSONResponse({
            "success": True,
            "message": "データを削除しました",
            "deleted_items": deleted_items,
        })

    except Exception as e:
        import traceback
        return JSONResponse({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status_code=500)


@app.get("/api/phase1_sessions/{paper_id}")
async def get_phase1_sessions(paper_id: str):
    """Phase1セッション履歴を取得"""
    try:
        sessions = data_manager.get_phase1_sessions(paper_id)
        return JSONResponse({
            "paper_id": paper_id,
            "sessions": sessions,
        })
    except Exception as e:
        return JSONResponse({
            "error": str(e)
        }, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
