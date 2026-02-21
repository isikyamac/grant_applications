from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv
import os


@dataclass
class CompanyConfig:
    name: str
    description: str
    focus_areas: list[str] = field(default_factory=list)
    eligibility: list[str] = field(default_factory=list)


@dataclass
class SearchConfig:
    keywords: list[str] = field(default_factory=list)


@dataclass
class Config:
    company: CompanyConfig
    search: SearchConfig
    anthropic_api_key: str
    sam_api_key: str
    google_api_key: str
    google_cse_id: str
    project_dir: Path

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        project_dir = Path(__file__).resolve().parent.parent
        if config_path is None:
            config_path = project_dir / "config.yaml"

        load_dotenv(project_dir / ".env")

        with open(config_path) as f:
            raw = yaml.safe_load(f)

        company = CompanyConfig(**raw.get("company", {}))
        search = SearchConfig(**raw.get("search", {}))
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        sam_api_key = os.environ.get("SAM_API_KEY", "")
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        google_cse_id = os.environ.get("GOOGLE_CSE_ID", "")

        return cls(
            company=company,
            search=search,
            anthropic_api_key=anthropic_api_key,
            sam_api_key=sam_api_key,
            google_api_key=google_api_key,
            google_cse_id=google_cse_id,
            project_dir=project_dir,
        )

    @property
    def db_path(self) -> Path:
        return self.project_dir / "grants.db"

    @property
    def proposals_dir(self) -> Path:
        return self.project_dir / "proposals"
