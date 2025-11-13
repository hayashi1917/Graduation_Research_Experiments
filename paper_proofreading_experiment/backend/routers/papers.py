"""
Paper management endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import shutil

from ..core.dependencies import get_paper_manager
from ..models.responses import PaperInfo, StandardResponse

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("/", response_model=List[PaperInfo])
async def get_papers():
    """Get list of all papers"""
    paper_manager = get_paper_manager()
    papers = paper_manager.list_papers()

    return [
        PaperInfo(
            id=paper["id"],
            pdf=paper["pdf"],
            tex=paper["tex"]
        )
        for paper in papers
    ]


@router.post("/upload")
async def upload_paper(
    paper_id: str = Form(...),
    pdf_file: UploadFile = File(...),
    tex_file: UploadFile = File(...)
):
    """Upload a new paper"""
    paper_manager = get_paper_manager()

    try:
        # Save PDF file
        pdf_path = paper_manager.paper_dir / paper_id / f"{paper_id}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        # Save TeX file
        tex_path = paper_manager.paper_dir / paper_id / f"{paper_id}.tex"

        with tex_path.open("wb") as buffer:
            shutil.copyfileobj(tex_file.file, buffer)

        return JSONResponse({
            "success": True,
            "message": f"論文 {paper_id} をアップロードしました",
            "paper": {
                "id": paper_id,
                "pdf": str(pdf_path),
                "tex": str(tex_path)
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}/info", response_model=PaperInfo)
async def get_paper_info(paper_id: str):
    """Get information about a specific paper"""
    paper_manager = get_paper_manager()

    pdf_path, tex_path = paper_manager.get_paper_paths(paper_id)

    if not pdf_path or not tex_path:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")

    return PaperInfo(
        id=paper_id,
        pdf=str(pdf_path),
        tex=str(tex_path)
    )
