from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv
import os


@dataclass
class CriterionConfig:
    name: str
    description: str
    weight: int


@dataclass
class EvaluatorConfig:
    anthropic_api_key: str
    project_dir: Path
    criteria_dir: str = "criteria"
    panel_size: int = 3
    temperature: float = 0.3
    model: str = "claude-sonnet-4-5-20250929"
    default_criteria: list[CriterionConfig] = field(default_factory=list)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "EvaluatorConfig":
        project_dir = Path(__file__).resolve().parent.parent
        if config_path is None:
            config_path = project_dir / "config.yaml"

        load_dotenv(project_dir / ".env")

        with open(config_path) as f:
            raw = yaml.safe_load(f)

        evaluator_raw = raw.get("evaluator", {})
        criteria_raw = evaluator_raw.get("default_criteria", [])
        default_criteria = [CriterionConfig(**c) for c in criteria_raw]

        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        return cls(
            anthropic_api_key=anthropic_api_key,
            project_dir=project_dir,
            criteria_dir=evaluator_raw.get("criteria_dir", "criteria"),
            panel_size=evaluator_raw.get("panel_size", 3),
            temperature=evaluator_raw.get("temperature", 0.3),
            model=evaluator_raw.get("model", "claude-sonnet-4-5-20250929"),
            default_criteria=default_criteria,
        )

    @property
    def db_path(self) -> Path:
        return self.project_dir / "grants.db"

    @property
    def criteria_path(self) -> Path:
        return self.project_dir / self.criteria_dir
