"""
FastAPI バックエンド - 論文校正実験用Web UI
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_client import LLMClient
from data_manager import DataManager
from response_parser import ResponseParser, ProofreadingIssue
from paper_manager import PaperManager
from phase1_cleaner import Phase1Cleaner
from phase2_embedder import Phase2Embedder
from phase3_proofreader import Phase3Proofreader

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
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# グローバル変数（実行状態管理）
current_execution = {
    "status": "idle",  # idle, running, paused, completed
    "phase": None,
    "paper_id": None,
    "iteration": 0,
    "pending_action": None,  # 判断待ちの指摘
}

# 設定とデータマネージャーの初期化
config_dir = Path(__file__).parent.parent / "config"
data_dir = Path(__file__).parent.parent / "data"
papers_dir = Path(__file__).parent.parent / "papers"

settings = yaml.safe_load((config_dir / "settings.yaml").read_text(encoding="utf-8"))
prompts = yaml.safe_load((config_dir / "prompts.yaml").read_text(encoding="utf-8"))
checklist = (config_dir / "checklist.md").read_text(encoding="utf-8")

data_manager = DataManager(data_dir=data_dir)
paper_manager = PaperManager(data_dir=data_dir)


@app.get("/")
async def read_root():
    """フロントエンドのindex.htmlを返す"""
    return FileResponse(frontend_path / "index.html")


@app.get("/api/papers")
async def get_papers():
    """登録されている論文のリストを取得"""
    papers = []
    if papers_dir.exists():
        for paper_dir in papers_dir.iterdir():
            if paper_dir.is_dir():
                pdf_files = list(paper_dir.glob("*.pdf"))
                tex_files = list(paper_dir.glob("*.tex"))
                if pdf_files and tex_files:
                    papers.append({
                        "id": paper_dir.name,
                        "pdf": pdf_files[0].name,
                        "tex": tex_files[0].name,
                    })
    return {"papers": papers}


@app.post("/api/papers/upload")
async def upload_paper(
    paper_id: str = Form(...),
    pdf_file: UploadFile = File(...),
    tex_file: UploadFile = File(...),
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

        # TeXファイルを保存
        tex_path = paper_dir / tex_file.filename
        with open(tex_path, "wb") as f:
            content = await tex_file.read()
            f.write(content)

        return {
            "status": "success",
            "message": f"論文 {paper_id} をアップロードしました",
            "pdf": pdf_file.filename,
            "tex": tex_file.filename,
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
        csv_path = data_dir / "iteration_log.csv"
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            # クライアントからのメッセージを処理
            if data.get("type") == "action":
                # ユーザーの判断を受信
                action = data.get("action")
                current_execution["user_action"] = action

                await manager.send_message({
                    "type": "action_received",
                    "action": action,
                }, websocket)

            elif data.get("type") == "start_phase":
                # フェーズ実行を開始
                paper_id = data.get("paper_id")
                phase = data.get("phase")

                # バックグラウンドで実行
                asyncio.create_task(execute_phase(paper_id, phase, websocket))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def execute_phase(paper_id: str, phase: str, websocket: WebSocket):
    """フェーズを実行（バックグラウンドタスク）"""
    try:
        current_execution["status"] = "running"
        current_execution["phase"] = phase
        current_execution["paper_id"] = paper_id

        # 論文ファイルのパスを取得
        paper_dir = papers_dir / paper_id
        pdf_files = list(paper_dir.glob("*.pdf"))
        tex_files = list(paper_dir.glob("*.tex"))

        if not pdf_files or not tex_files:
            await manager.send_message({
                "type": "error",
                "message": "論文ファイルが見つかりません",
            }, websocket)
            return

        pdf_path = pdf_files[0]
        tex_path = tex_files[0]

        # LLMクライアントの初期化
        if phase in ["phase1", "phase3"]:
            llm_config = settings["llm"]["proofreading"]
        else:  # phase2
            llm_config = settings["llm"]["error_embedding"]

        llm_client = LLMClient(
            provider=llm_config["provider"],
            model=llm_config["model"],
            temperature=llm_config.get("temperature", 0.0),
            api_key=None,  # 環境変数から取得
        )

        # フェーズ実行
        if phase == "phase1":
            await execute_phase1(paper_id, pdf_path, tex_path, llm_client, websocket)
        elif phase == "phase2":
            await execute_phase2(paper_id, pdf_path, tex_path, llm_client, websocket)
        elif phase == "phase3":
            await execute_phase3(paper_id, pdf_path, tex_path, llm_client, websocket)

        current_execution["status"] = "idle"

    except Exception as e:
        await manager.send_message({
            "type": "error",
            "message": str(e),
        }, websocket)
        current_execution["status"] = "idle"


async def execute_phase1(paper_id: str, pdf_path: Path, tex_path: Path, llm_client: LLMClient, websocket: WebSocket):
    """フェーズ1を実行"""
    # Phase1Cleanerの実装をWebSocket対応に修正する必要がある
    # ここでは簡略化のため、基本的な流れのみ実装

    await manager.send_message({
        "type": "phase_start",
        "phase": "phase1",
        "message": "フェーズ1: クリーン化を開始",
    }, websocket)

    # 実装中...
    await manager.send_message({
        "type": "phase_complete",
        "phase": "phase1",
        "message": "フェーズ1が完了しました",
    }, websocket)


async def execute_phase2(paper_id: str, pdf_path: Path, tex_path: Path, llm_client: LLMClient, websocket: WebSocket):
    """フェーズ2を実行"""
    await manager.send_message({
        "type": "phase_start",
        "phase": "phase2",
        "message": "フェーズ2: エラー埋め込みを開始",
    }, websocket)

    # 実装中...
    await manager.send_message({
        "type": "phase_complete",
        "phase": "phase2",
        "message": "フェーズ2が完了しました",
    }, websocket)


async def execute_phase3(paper_id: str, pdf_path: Path, tex_path: Path, llm_client: LLMClient, websocket: WebSocket):
    """フェーズ3を実行"""
    await manager.send_message({
        "type": "phase_start",
        "phase": "phase3",
        "message": "フェーズ3: 校正を開始",
    }, websocket)

    # 実装中...
    await manager.send_message({
        "type": "phase_complete",
        "phase": "phase3",
        "message": "フェーズ3が完了しました",
    }, websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
