"""
Response models
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PaperInfo(BaseModel):
    """Paper information"""
    id: str
    pdf: str
    tex: str


class Phase1SessionInfo(BaseModel):
    """Phase1 session information"""
    phase1_id: str
    paper_id: str
    started_at: str
    completed_at: str = ""
    iterations: int = 0
    excluded_items: List[str] = []
    status: str = "in_progress"  # in_progress, completed, aborted
    final_tex_path: str = ""
    final_pdf_path: str = ""


class IterationInfo(BaseModel):
    """Iteration information"""
    session_id: str
    paper_id: str
    phase: str
    iteration: int
    timestamp: str
    detected_errors: List[str]
    new_issues_count: int


class DetectionRateInfo(BaseModel):
    """Detection rate information"""
    total_embedded: int
    total_detected: int
    detection_rate: float


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
