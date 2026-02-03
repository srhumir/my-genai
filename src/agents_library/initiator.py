from pathlib import Path

from src.agents_library import build_agent_settings
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

        agent_settings = build_agent_settings(settings, config_path)
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
            f"Loaded agent from: {agent.agent_settings.agent_config.name}, *** {agent.agent_settings.agent_config.description}"
        )
