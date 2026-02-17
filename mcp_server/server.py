from collections.abc import Callable, Coroutine
from logging import getLogger
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from src.agents_library import build_agent_settings
from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.initiator import load_agent_paths
from src.agents_library.memory import ConversationMemory
from src.agents_library.response_types import BaseChatResponse
from src.config.settings import Settings, settings

load_dotenv()
logger = getLogger(__name__)

mcp_app = FastMCP(
    name="my-mcp-server",
    version="0.0.1",
    instructions="access AI agents and tools for various tasks",
)

session_config = ChatSessionConfig(
    bot_user_name="TestBot",
    session_id="session_123",
    topic_id="topic_abc",
)

agent_path_list = load_agent_paths()


# Helper to capture loop variables per tool registration
def _make_tool_handler(
    *,
    bound_agent_settings: Settings,
    bound_agent_path: Path,
    bound_session_config: ChatSessionConfig,
) -> Callable[[str], Coroutine[Any, Any, str]]:
    async def _handler(query: str) -> str:
        memory = ConversationMemory()
        agent = BaseAgent(
            settings=bound_agent_settings,
            session_config=bound_session_config,
            memory=memory,
            agent_folder_path=bound_agent_path,
        )
        response: str = await agent.prepare_response(query, BaseChatResponse)
        return response

    return _handler


for agent_path in agent_path_list:
    logger.info(f"Loading agent from path: {agent_path}")
    agent_settings = build_agent_settings(settings, agent_path / "agent_config.yaml")
    tool_name: str = agent_settings.agent_config.name.lower().replace(" ", "_")
    tool_desc: str = agent_settings.agent_config.description

    handler = _make_tool_handler(
        bound_agent_settings=agent_settings,
        bound_agent_path=agent_path,
        bound_session_config=session_config,
    )

    mcp_app.tool(name=tool_name, description=tool_desc)(handler)
