"""
Dependency injection for FastAPI
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from llm_client import LLMClient, GeminiClient, ClaudeClient
from data_manager import DataManager
from paper_manager import PaperManager
from .config import settings


# Initialize managers (singleton pattern)
_data_manager = None
_paper_manager = None


def get_data_manager() -> DataManager:
    """Get DataManager instance"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(results_dir=settings.results_dir)
    return _data_manager


def get_paper_manager() -> PaperManager:
    """Get PaperManager instance"""
    global _paper_manager
    if _paper_manager is None:
        _paper_manager = PaperManager(
            paper_dir=settings.papers_dir,
            versions_dir=settings.versions_dir
        )
    return _paper_manager


def get_llm_client(provider: str = None, model: str = None) -> LLMClient:
    """
    Get LLM client instance

    Args:
        provider: LLM provider ('gemini' or 'claude')
        model: Model name

    Returns:
        LLMClient instance
    """
    if provider is None:
        provider = settings.settings.get("llm", {}).get("provider", "gemini")

    if model is None:
        model = settings.settings.get("llm", {}).get("model", "gemini-1.5-pro")

    if provider.lower() == "gemini":
        return GeminiClient(model=model)
    elif provider.lower() == "claude":
        return ClaudeClient(model=model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
