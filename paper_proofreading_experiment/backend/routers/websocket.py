"""
WebSocket endpoints for real-time communication
"""
import asyncio
import sys
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import os

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from llm_client import GeminiClient, ClaudeClient
from ..websocket_adapters import WebSocketPhase1Adapter, WebSocketPhase2Adapter, WebSocketPhase3Adapter

router = APIRouter()


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


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket接続"""
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
                from ..core.dependencies import get_paper_manager, get_data_manager
                from ..core.config import settings

                papers_dir = settings.papers_dir
                versions_dir = settings.versions_dir

                asyncio.create_task(
                    execute_phase(
                        paper_id, phase, websocket, client_id,
                        papers_dir, versions_dir
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocketエラー: {e}")
        manager.disconnect(client_id)


async def execute_phase(
    paper_id: str, phase: str, websocket: WebSocket, client_id: str,
    papers_dir: Path, versions_dir: Path
):
    """フェーズを実行（バックグラウンドタスク）"""
    try:
        from ..core.dependencies import get_data_manager, get_paper_manager
        from ..core.config import settings

        data_manager = get_data_manager()
        paper_manager = get_paper_manager()

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
            llm_config = settings.settings["llm"]["proofreading"]
        else:  # phase2
            llm_config = settings.settings["llm"]["error_embedding"]

        # APIキーを環境変数から取得
        provider = llm_config["provider"]
        model = llm_config["model"]
        temperature = llm_config.get("temperature", 0.0)

        if provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("環境変数 GOOGLE_API_KEY または GEMINI_API_KEY が設定されていません")
            llm_client = GeminiClient(model=model, api_key=api_key, temperature=temperature)
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("環境変数 ANTHROPIC_API_KEY が設定されていません")
            llm_client = ClaudeClient(model=model, api_key=api_key, temperature=temperature)
        else:
            raise ValueError(f"未対応のプロバイダー: {provider}")

        # フェーズ実行
        if phase == "phase1":
            await execute_phase1(
                paper_id, pdf_path, tex_path, llm_client, websocket, client_id,
                data_manager, paper_manager, settings, versions_dir
            )
        elif phase == "phase2":
            await execute_phase2(
                paper_id, pdf_path, tex_path, llm_client, websocket, client_id,
                data_manager, settings
            )
        elif phase == "phase3":
            await execute_phase3(
                paper_id, pdf_path, tex_path, llm_client, websocket, client_id,
                data_manager, paper_manager, settings
            )

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        await manager.send_message({
            "type": "error",
            "message": error_msg,
        }, client_id)


async def execute_phase1(
    paper_id: str, pdf_path: Path, tex_path: Path, llm_client, websocket: WebSocket,
    client_id: str, data_manager, paper_manager, settings, versions_dir: Path
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
            prompt_template=settings.prompts["prompt_a_and_c"]["template"],
            checklist=settings.checklist,
            versions_dir=versions_dir,
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
    paper_id: str, pdf_path: Path, tex_path: Path, llm_client, websocket: WebSocket,
    client_id: str, data_manager, settings
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
            prompt_template=settings.prompts["prompt_b"]["template"],
            checklist=settings.checklist,
            num_errors=settings.settings["experiment"]["num_errors"],
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
    paper_id: str, pdf_path: Path, tex_path: Path, llm_client, websocket: WebSocket,
    client_id: str, data_manager, paper_manager, settings
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
            prompt_template=settings.prompts["prompt_a_and_c"]["template"],
            checklist=settings.checklist,
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
