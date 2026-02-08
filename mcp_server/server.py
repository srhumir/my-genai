from dotenv import load_dotenv
from fastmcp import FastMCP

from src.agents_library.base import ChatSessionConfig
from src.agents_library.initiator import load_agents
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

agent_list = load_agents(settings, session_config)

for agent in agent_list:
    tool_name = agent.agent_settings.agent_config.name.lower().replace(" ", "_")
    tool_desc = agent.agent_settings.agent_config.description

    @mcp_app.tool(name=tool_name, description=tool_desc)
    async def tool_func(query: str) -> str:
        response = await agent.prepare_response(query, BaseChatResponse)
        return response
