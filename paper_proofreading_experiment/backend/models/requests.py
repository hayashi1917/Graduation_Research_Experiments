"""
Request models
"""
from pydantic import BaseModel, Field
from typing import Optional


class ResetRequest(BaseModel):
    """Data reset request"""
    reset_results: bool = Field(default=False, description="Reset experimental results")
    reset_versions: bool = Field(default=False, description="Reset version history")
    reset_progress: bool = Field(default=False, description="Reset progress information")


class SettingsUpdateRequest(BaseModel):
    """Settings update request"""
    llm_provider: Optional[str] = Field(None, description="LLM provider")
    llm_model: Optional[str] = Field(None, description="LLM model name")


class PhaseExecutionRequest(BaseModel):
    """Phase execution request"""
    paper_id: str = Field(..., description="Paper ID")
    phase1_id: Optional[str] = Field(None, description="Phase1 session ID (for Phase2/3)")
