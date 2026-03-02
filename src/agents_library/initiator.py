from pathlib import Path

from src.agents_library import build_agent_settings
from src.config.settings import settings


def validate_agent_folder(agent_path: Path) -> None:
    """Validate one agent folder for required files and config schema validity."""
    config_path = agent_path / "agent_config.yaml"
    prompt_path = agent_path / "system_prompt.md"

    if not config_path.exists():
        raise FileNotFoundError(f"Missing agent_config.yaml in {agent_path}")
    if not prompt_path.exists():
        raise FileNotFoundError(f"Missing system_prompt.md in {agent_path}")

    # schema + model format validation happen in build_agent_settings/AgentConfig
    build_agent_settings(settings, config_path)


def load_agent_paths(
    agents_root: str | Path | None = None,
) -> list[Path]:
    """List and validate all agent folders in the agents library directory."""
    root = Path(agents_root) if agents_root else Path(__file__).parent / "agents"
    if not root.is_dir():
        raise FileNotFoundError(f"Agents root not found: {root}")

    agent_path_list: list[Path] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            validate_agent_folder(entry)
            agent_path_list.append(entry)

    return agent_path_list


if __name__ == "__main__":
    agents = load_agent_paths()
    for agent in agents:
        print(f"Loaded agent from: {agent}")
