"""
Application configuration
"""
from pathlib import Path
import yaml


class Settings:
    """Application settings"""

    def __init__(self):
        # Paths
        self.backend_dir = Path(__file__).parent.parent
        self.project_dir = self.backend_dir.parent
        self.config_dir = self.project_dir / "config"
        self.data_dir = self.project_dir / "data"
        self.papers_dir = self.project_dir / "papers"

        # Create directories
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Sub-directories
        self.results_dir = self.data_dir / "results"
        self.versions_dir = self.data_dir / "versions"
        self.logs_dir = self.data_dir / "logs"

        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration files
        self.settings = yaml.safe_load(
            (self.config_dir / "settings.yaml").read_text(encoding="utf-8")
        )
        self.prompts = yaml.safe_load(
            (self.config_dir / "prompts.yaml").read_text(encoding="utf-8")
        )
        self.checklist = (self.config_dir / "checklist.md").read_text(encoding="utf-8")

        # Server settings
        self.host = "0.0.0.0"
        self.port = 8000
        self.cors_origins = ["*"]


# Global settings instance
settings = Settings()
