"""
Data management endpoints
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import List
import shutil

from ..core.dependencies import get_data_manager
from ..core.config import settings
from ..models.requests import ResetRequest
from ..models.responses import Phase1SessionInfo, DetectionRateInfo, IterationInfo

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/reset")
async def reset_data(request: ResetRequest):
    """Reset experimental data"""
    deleted_items = []

    try:
        if request.reset_results:
            # Delete experimental results
            if settings.results_dir.exists():
                # Delete CSV and JSON files (keep directory)
                for file in settings.results_dir.glob("*.csv"):
                    file.unlink()
                    deleted_items.append(str(file.name))
                for file in settings.results_dir.glob("*.json"):
                    file.unlink()
                    deleted_items.append(str(file.name))

                # Reinitialize DataManager to create CSV headers
                from ..core.dependencies import _data_manager
                from data_manager import DataManager
                _data_manager = DataManager(results_dir=settings.results_dir)

        if request.reset_versions:
            # Delete version history
            if settings.versions_dir.exists():
                shutil.rmtree(settings.versions_dir)
                settings.versions_dir.mkdir(parents=True, exist_ok=True)
                deleted_items.append("versions/")

        if request.reset_progress:
            # Delete progress information
            progress_file = settings.results_dir / "progress.json"
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


@router.get("/phase1_sessions/{paper_id}", response_model=List[Phase1SessionInfo])
async def get_phase1_sessions(paper_id: str):
    """Get Phase1 session history for a paper"""
    data_manager = get_data_manager()

    try:
        sessions = data_manager.get_phase1_sessions(paper_id)
        return [Phase1SessionInfo(**session) for session in sessions]
    except Exception as e:
        return JSONResponse({
            "error": str(e)
        }, status_code=500)


@router.get("/iterations/{paper_id}")
async def get_iterations(paper_id: str):
    """Get iteration history for a paper"""
    # TODO: Implement iteration retrieval from CSV
    # This is a placeholder for now
    return JSONResponse({
        "paper_id": paper_id,
        "iterations": []
    })


@router.get("/detection_rate/{paper_id}", response_model=DetectionRateInfo)
async def get_detection_rate(paper_id: str):
    """Get detection rate for a paper"""
    data_manager = get_data_manager()

    try:
        rate_info = data_manager.calculate_detection_rate(paper_id)
        return DetectionRateInfo(**rate_info)
    except Exception as e:
        return JSONResponse({
            "error": str(e)
        }, status_code=500)
