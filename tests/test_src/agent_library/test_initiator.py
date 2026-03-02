from pathlib import Path

import pytest

from src.agents_library import build_agent_settings
from src.agents_library.initiator import load_agent_paths
from src.config.settings import Settings


def test_load_agent_paths_validates_required_files(tmp_path: Path) -> None:
    root = tmp_path / "agents"
    agent_dir = root / "broken_agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent_config.yaml").write_text(
        "name: A\ndescription: B\nmodel: openai/gpt-4o\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="system_prompt.md"):
        load_agent_paths(root)


def test_build_agent_settings_requires_explicit_required_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "agent_config.yaml"
    config_path.write_text(
        "description: Missing name\nmodel: openai/gpt-4o\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="name"):
        build_agent_settings(Settings(), config_path)


def test_build_agent_settings_rejects_invalid_model_format(tmp_path: Path) -> None:
    config_path = tmp_path / "agent_config.yaml"
    config_path.write_text(
        "name: A\ndescription: B\nmodel: gpt-4o\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="provider"):
        build_agent_settings(Settings(), config_path)
