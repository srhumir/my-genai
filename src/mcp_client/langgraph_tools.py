from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field, create_model

from src.mcp_client.client import MCPClient


class _MCPToolInputBase(BaseModel):
    """Base schema that allows additional MCP tool fields at runtime."""

    model_config = ConfigDict(extra="allow")


async def _invoke_mcp_tool(tool_name: str, **kwargs: Any) -> str:
    """Invoke an MCP tool asynchronously and return its string result."""
    async with MCPClient() as client:
        return await client.call(tool_name, args=kwargs)


def _build_schema(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Create a permissive pydantic args schema from MCP/OpenAI JSON schema."""
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields: dict[str, tuple[Any, Any]] = {}
    for field_name in properties:
        default = ... if field_name in required else None
        fields[field_name] = (Any, Field(default=default))

    model_name = f"{tool_name.title().replace('_', '')}Input"
    if fields:
        return create_model(model_name, __base__=_MCPToolInputBase, **fields)
    return create_model(model_name, __base__=_MCPToolInputBase)


def openai_tool_to_langchain(tool_payload: dict[str, Any]) -> StructuredTool:
    """Convert one OpenAI-style function tool definition to StructuredTool."""
    function_spec = tool_payload["function"]
    tool_name = function_spec["name"]
    description = function_spec.get("description", "")
    schema = function_spec.get("parameters") or {"type": "object", "properties": {}}
    args_schema = _build_schema(tool_name, schema)

    async def _tool_callable(**kwargs: Any) -> str:
        return await _invoke_mcp_tool(tool_name, **kwargs)

    return StructuredTool.from_function(
        name=tool_name,
        description=description,
        coroutine=_tool_callable,
        args_schema=args_schema,
    )


def openai_tools_to_langchain(tools: list[dict[str, Any]]) -> list[StructuredTool]:
    """Convert a list of OpenAI-style tool payloads to LangChain tools."""

    return [openai_tool_to_langchain(tool) for tool in tools]
