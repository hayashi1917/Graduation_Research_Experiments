"""
Paper management endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import shutil

from ..core.dependencies import get_paper_manager
from ..core.config import settings
from ..models.responses import PaperInfo, StandardResponse

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("/", response_model=List[PaperInfo])
async def get_papers():
    """Get list of all papers"""
    papers = []
    papers_dir = settings.papers_dir

    if papers_dir.exists():
        for paper_dir in papers_dir.iterdir():
            if paper_dir.is_dir():
                pdf_files = list(paper_dir.glob("*.pdf"))
                if pdf_files:
                    papers.append(
                        PaperInfo(
                            id=paper_dir.name,
                            pdf=pdf_files[0].name
                        )
                    )

    return papers


@router.post("/upload")
async def upload_paper(
    paper_id: str = Form(...),
    pdf_file: UploadFile = File(...)
):
    """Upload a new paper"""
    paper_manager = get_paper_manager()

    try:
        # Save PDF file
        pdf_path = paper_manager.paper_dir / paper_id / f"{paper_id}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        return JSONResponse({
            "success": True,
            "message": f"論文 {paper_id} をアップロードしました",
            "paper": {
                "id": paper_id,
                "pdf": str(pdf_path)
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}/info", response_model=PaperInfo)
async def get_paper_info(paper_id: str):
    """Get information about a specific paper"""
    papers_dir = settings.papers_dir
    paper_dir = papers_dir / paper_id

    if not paper_dir.exists() or not paper_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")

    pdf_files = list(paper_dir.glob("*.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail=f"Paper files not found for {paper_id}")

    return PaperInfo(
        id=paper_id,
        pdf=pdf_files[0].name
    )
