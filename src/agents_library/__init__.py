from pathlib import Path

import yaml

from src.config.settings import AgentConfig, Settings


def build_agent_settings(settings: Settings, config_path: Path) -> Settings:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"agent_config.yaml must contain a mapping at {config_path}")

    merged = settings.agent_config.model_dump()
    merged.update(raw)
    agent_config = AgentConfig(**merged)

    return settings.model_copy(deep=True, update={"agent_config": agent_config})


__all__ = ["build_agent_settings"]
