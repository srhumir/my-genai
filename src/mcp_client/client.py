from logging import getLogger
from typing import Any

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from mcp import Tool
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import ResourceLink, TextContent

from src.config.settings import MCPClientConfig, settings

logger = getLogger(__name__)


class MCPClient:
    def __init__(self, config: MCPClientConfig | None = None):
        self.config = config or settings.mcp_server_config
        self._conn_ctx: Any | None = None
        self._session_ctx: Any | None = None
        self._read: Any | None = None
        self._write: Any | None = None
        self._session: ClientSession | None = None
        self._connected: bool = False

    async def list_tools(self) -> list[Tool]:
        session = self._require_session()
        logger.info("listing tools from MCP server")
        lt = await session.list_tools()
        logger.debug(f"tools: {lt.tools}")
        return lt.tools

    async def call(self, tool_name: str, args: dict[str, Any]) -> str:
        session = self._require_session()
        logger.info(f"calling MCP tool {tool_name} with args {args}")
        resp = await session.call_tool(tool_name, args or {})
        for part in resp.content:
            if isinstance(part, TextContent):
                return part.text
            if isinstance(part, ResourceLink):
                return part.uri.unicode_string()
        logger.warning(f"Unknown response type from tool {tool_name} with args {args}")
        logger.warning(f"the response content was: {resp.content}")
        return "no result"

    async def get_openai_tools(self) -> list[ChatCompletionToolParam]:
        """Helper method to fetch MCP tools and convert them to OpenAI tool format."""
        mcp_tools = await self.list_tools()
        return tools_as_openai_tools(mcp_tools)

    async def __aenter__(self) -> "MCPClient":
        self._conn_ctx = streamable_http_client(self.config.mcp_server_url)
        self._read, self._write, _ = await self._conn_ctx.__aenter__()
        self._session_ctx = ClientSession(self._read, self._write)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()
        self._connected = True
        return self

    async def __aexit__(
        self, exc_type: type | None, exc: BaseException | None, tb: Any | None
    ) -> None:
        if self._session_ctx:
            await self._session_ctx.__aexit__(exc_type, exc, tb)
        if self._conn_ctx:
            await self._conn_ctx.__aexit__(exc_type, exc, tb)
        self._connected = False
        self._session = None
        self._session_ctx = None
        self._conn_ctx = None
        self._read = None
        self._write = None

    def _require_session(self) -> ClientSession:
        if not self._connected or self._session is None:
            raise RuntimeError("MCPClient must be used within an 'async with' context.")
        return self._session


def tools_as_openai_tools(mcp_tools: list[Tool]) -> list[ChatCompletionToolParam]:
    """Map MCP tool schemas to OpenAI function-tools."""
    out = []
    for tool in mcp_tools:
        schema = tool.inputSchema or {"type": "object", "properties": {}}
        out.append(
            ChatCompletionToolParam(
                type="function",
                function=ChatCompletionToolParamFunctionChunk(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=schema,
                ),
            )
        )
    return out
