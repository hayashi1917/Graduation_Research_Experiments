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

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient
from data_manager import DataManager
from response_parser import ResponseParser
from paper_manager import PaperManager
from websocket_adapters import WebSocketPhase1Adapter, WebSocketPhase3Adapter

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

results_dir.mkdir(parents=True, exist_ok=True)
versions_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)

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

                # 実行中のアダプターにアクションを通知
                adapter = manager.get_adapter(client_id)
                if adapter:
                    adapter.set_user_action(action)

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
        tex_files = list(paper_dir.glob("*.tex"))

        if not pdf_files or not tex_files:
            await manager.send_message({
                "type": "error",
                "message": "論文ファイルが見つかりません",
            }, client_id)
            return

        pdf_path = pdf_files[0]
        tex_path = tex_files[0]

        # LLMクライアントの初期化
        if phase in ["phase1", "phase3"]:
            llm_config = settings["llm"]["proofreading"]
        else:  # phase2
            llm_config = settings["llm"]["error_embedding"]

        # APIキーを環境変数から取得
        api_key = None
        if llm_config["provider"] == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
        elif llm_config["provider"] == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")

        llm_client = LLMClient(
            provider=llm_config["provider"],
            model=llm_config["model"],
            temperature=llm_config.get("temperature", 0.0),
            api_key=api_key,
        )

        # フェーズ実行
        if phase == "phase1":
            await execute_phase1(paper_id, pdf_path, tex_path, llm_client, websocket, client_id)
        elif phase == "phase2":
            await execute_phase2(paper_id, pdf_path, tex_path, llm_client, websocket, client_id)
        elif phase == "phase3":
            await execute_phase3(paper_id, pdf_path, tex_path, llm_client, websocket, client_id)

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
    tex_path: Path,
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
            prompt_template=prompts["prompt_a_and_c"],
            checklist=checklist,
            max_iterations=settings["experiment"]["max_iterations"],
        )

        # アダプターを登録
        manager.set_adapter(client_id, adapter)

        # 実行
        result = await adapter.run(
            paper_id=paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
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
    tex_path: Path,
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

        # 除外項目を取得
        excluded_items = data_manager.get_excluded_items(paper_id)
        excluded_items_str = "\n".join([f"- {item}" for item in excluded_items]) if excluded_items else "なし"

        # プロンプトを構築
        prompt = prompts["prompt_b"].format(
            num_errors=settings["experiment"]["num_errors"],
            max_errors_per_item=settings["experiment"]["max_errors_per_item"],
            excluded_items=excluded_items_str,
            checklist=checklist,
        )

        # プロンプトを保存
        data_manager.save_prompt(
            paper_id=paper_id,
            phase="phase2",
            iteration=1,
            prompt=prompt,
        )

        await manager.send_message({
            "type": "log",
            "message": "LLMにエラー埋め込みを依頼中...",
            "level": "info"
        }, client_id)

        # LLMを呼び出す
        response = llm_client.call(
            prompt=prompt,
            pdf_path=pdf_path,
            tex_path=tex_path,
        )

        # 応答を保存
        data_manager.save_response(
            paper_id=paper_id,
            phase="phase2",
            iteration=1,
            response=response,
        )

        await manager.send_message({
            "type": "llm_response",
            "message": "LLMの応答を受信しました",
        }, client_id)

        await manager.send_message({
            "type": "log",
            "message": f"エラー埋め込みの提案を受信しました\n\n{response[:1000]}...",
            "level": "info"
        }, client_id)

        await manager.send_message({
            "type": "log",
            "message": "手動で論文ファイルにエラーを埋め込んでください",
            "level": "warning"
        }, client_id)

        await manager.send_message({
            "type": "phase_complete",
            "phase": "phase2",
            "message": "フェーズ2が完了しました。提案されたエラーを確認し、手動で論文に反映してください。",
        }, client_id)

    except Exception as e:
        import traceback
        await manager.send_message({
            "type": "error",
            "message": f"フェーズ2実行エラー: {str(e)}\n{traceback.format_exc()}",
        }, client_id)


async def execute_phase3(
    paper_id: str,
    pdf_path: Path,
    tex_path: Path,
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
            prompt_template=prompts["prompt_a_and_c"],
            checklist=checklist,
            max_iterations=settings["experiment"]["max_iterations"],
        )

        # アダプターを登録
        manager.set_adapter(client_id, adapter)

        # 実行
        result = await adapter.run(
            paper_id=paper_id,
            pdf_path=pdf_path,
            tex_path=tex_path,
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
