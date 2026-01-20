from pathlib import Path

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.memory import ConversationMemory
from src.config.settings import Settings


def load_agents(
    settings: Settings,
    session_config: ChatSessionConfig,
    agents_root: str | Path | None = None,
) -> list[BaseAgent]:
    """Load all agents under the agents library directory."""
    root = Path(agents_root) if agents_root else Path(__file__).parent / "agents"
    if not root.is_dir():
        raise FileNotFoundError(f"Agents root not found: {root}")

    agents: list[BaseAgent] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        config_path = entry / "agent_config.yaml"
        prompt_path = entry / "system_prompt.md"
        if not config_path.is_file() or not prompt_path.is_file():
            raise FileNotFoundError(
                f"Missing agent_config.yaml or system_prompt.md in {entry}"
            )

        memory = ConversationMemory()
        agents.append(
            BaseAgent(
                settings=settings,
                session_config=session_config,
                memory=memory,
                agent_folder_path=str(entry),
            )
        )

    return agents


__all__ = ["load_agents", "BaseAgent", "ChatSessionConfig"]
