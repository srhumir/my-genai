from pathlib import Path

import yaml

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.memory import ConversationMemory
from src.config.settings import AgentConfig, Settings


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

        agent_settings = _build_agent_settings(settings, config_path)
        memory = ConversationMemory()
        agents.append(
            BaseAgent(
                settings=agent_settings,
                session_config=session_config,
                memory=memory,
                agent_folder_path=str(entry),
            )
        )

    return agents


def _build_agent_settings(settings: Settings, config_path: Path) -> Settings:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"agent_config.yaml must contain a mapping at {config_path}")

    merged = settings.agent_config.model_dump()
    merged.update(raw)
    agent_config = AgentConfig(**merged)

    return settings.model_copy(deep=True, update={"agent_config": agent_config})


if __name__ == "__main__":
    settings = Settings()
    session_config = ChatSessionConfig(
        bot_user_name="TestBot",
        session_id="session_123",
        topic_id="topic_abc",
    )
    agents = load_agents(settings, session_config)
    for agent in agents:
        print(
            f"Loaded agent from: {agent.settings.agent_config.name}, *** {agent.settings.agent_config.description}"
        )
