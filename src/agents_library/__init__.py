from pathlib import Path

import yaml

from src.config.settings import AgentConfig, Settings

_REQUIRED_FIELDS = {"name", "description", "model"}


def build_agent_settings(settings: Settings, config_path: Path) -> Settings:
    """Build per-agent settings from YAML while enforcing required agent fields."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"agent_config.yaml must contain a mapping at {config_path}")

    # Keep global defaults only for optional fields so each agent explicitly
    # declares required identity/model fields.
    base_config = settings.agent_config.model_dump(exclude=_REQUIRED_FIELDS)
    merged = {**base_config, **raw}
    agent_config = AgentConfig(**merged)

    return settings.model_copy(deep=True, update={"agent_config": agent_config})


__all__ = ["build_agent_settings"]
