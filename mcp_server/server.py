from dotenv import load_dotenv
from fastmcp import FastMCP

from src.agents_library import build_agent_settings
from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.initiator import load_agent_paths
from src.agents_library.memory import ConversationMemory
from src.agents_library.response_types import BaseChatResponse
from src.config.settings import settings

load_dotenv()

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

for agent_path in agent_path_list:
    agent_config = build_agent_settings(settings, agent_path / "agent_config.yaml")
    tool_name = agent_config.name.lower().replace(" ", "_")
    tool_desc = agent_config.description

    @mcp_app.tool(name=tool_name, description=tool_desc)
    async def tool_func(query: str) -> str:
        memory = ConversationMemory()
        agent = BaseAgent(
            settings=agent_config,
            session_config=session_config,
            memory=memory,
            agent_folder_path=agent_path,
        )
        response = await agent.prepare_response(query, BaseChatResponse)
        return response
