import asyncio
import importlib.util
import json
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, cast

from async_lru import alru_cache
from litellm import (  # type: ignore[attr-defined]
    BadRequestError,
    ChatCompletionToolParam,
)

from src.agents_library import build_agent_settings
from src.agents_library.memory import ConversationMemory
from src.agents_library.response_types import BaseChatResponse
from src.api_client.chat_client import ChatClient
from src.config.settings import Settings
from src.mcp_client.client import MCPClient

logger = getLogger(__name__)


@dataclass
class ChatSessionConfig:
    bot_user_name: str
    session_id: str
    topic_id: str


class BaseAgent:
    def __init__(
        self,
        settings: Settings,
        session_config: ChatSessionConfig,
        memory: ConversationMemory,
        agent_folder_path: str | Path,
    ) -> None:
        """Initialize a BaseAgent that orchestrates LLM chat interactions with optional MCP tooling.

        This class manages conversation memory, builds system prompts, calls the chat client,
        and executes MCP tools requested by the LLM. It also caches available MCP tools.

        Args:
            settings: Global application settings including agent_config (model, tools, paths).
            session_config: Per-chat session configuration such as response language and bot name.
            memory: ConversationMemory used to store user/assistant messages and tool results.
            agent_folder_path: relative path to the folder containing agent config and prompt.
        """
        self.agent_folder_path = Path(agent_folder_path)
        self.agent_settings = build_agent_settings(
            settings, self.agent_folder_path / "agent_config.yaml"
        )
        self.session_config = session_config
        self.memory = memory
        self._cached_tools: list[ChatCompletionToolParam] | None = None
        self._client = ChatClient(self.agent_settings)

    async def get_system_prompt(self) -> str:
        """Generate the system prompt for the agent by loading system_prompt.md and applying replacements.

        Then ensure the '## AVAILABLE TOOLS:' section contains the current tool descriptions. If the section
        does not exist and tools are available, append it to the end of the prompt.
        """
        tool_description_list = [
            f"* {tool["function"]["name"]}: {tool["function"]["description"].split("\n")[0]}"
            for tool in await self.get_tools()
        ]
        prompt_path = self.agent_folder_path / "system_prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"system_prompt.md not found at: {prompt_path}")
        content = prompt_path.read_text(encoding="utf-8")
        content = self._replace_variables_in_prompt(content)

        if tool_description_list:
            section_header = "## AVAILABLE TOOLS:"
            header_idx = content.find(section_header)
            if header_idx != -1:
                # Find end of section by next header or EOF
                after_header_idx = header_idx + len(section_header)
                next_header_idx = content.find("\n## ", after_header_idx)
                if next_header_idx == -1:
                    next_header_idx = len(content)
                existing_section = content[after_header_idx:next_header_idx]
                if not existing_section.endswith("\n"):
                    existing_section = existing_section + "\n"
                updated_section = (
                    existing_section + "\n".join(tool_description_list) + "\n"
                )
                content = (
                    content[:after_header_idx]
                    + updated_section
                    + content[next_header_idx:]
                )
            else:
                if not content.endswith("\n"):
                    content += "\n"
                content += (
                    f"\n{section_header}\n" + "\n".join(tool_description_list) + "\n"
                )

        return content

    @alru_cache
    async def get_tools(self) -> list[ChatCompletionToolParam]:
        """Fetch MCP tools filtered by settings.agent_config.my_mcp_tools."""
        if self.agent_settings.agent_config.my_mcp_tools is None:
            return []

        async with MCPClient() as mcp_client:
            all_mcp_tools: list[
                ChatCompletionToolParam
            ] = await mcp_client.get_openai_tools()

        allowed = set(self.agent_settings.agent_config.my_mcp_tools or [])
        return [t for t in all_mcp_tools if t["function"]["name"] in allowed]

    @alru_cache
    async def get_initial_action_prompts(self) -> dict[str, str]:
        """Parse initial_action_prompts.md into sections keyed by header.

        Reads the agent's initial_action_prompts.md, applies variable replacements,
        and returns a dict mapping each Markdown header line (starting with '#') to
        the section content until the next header or end of file. If the file does
        not exist, returns an empty dict.
        This dic is later used to present initial action options to the user in the frontend.
        """
        prompt_path = self.agent_folder_path / "initial_action_prompts.md"
        if not prompt_path.exists():
            logger.info(f"initial_action_prompts.md not found at: {prompt_path}")
            return {}

        content = prompt_path.read_text(encoding="utf-8")
        content = self._replace_variables_in_prompt(content)

        sections: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            if line.lstrip().startswith("#"):
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip()

                header = line.lstrip().lstrip("#").strip()
                current_key = header
                current_lines = []
            else:
                if current_key is not None:
                    current_lines.append(line)

        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

        return sections

    async def prepare_response(
        self, message: str, response_format: type[BaseChatResponse] = BaseChatResponse
    ) -> str:
        self.memory.add_user(message)
        logger.info("Initial call to model via LiteLLM")
        await self._call_llm(tool_choice="auto", response_format=response_format)
        assistant_message = self.memory.messages[-1]
        if assistant_message.get("tool_calls"):
            await self._add_tool_results_to_memory(assistant_message)
            logger.info("Final call to model after tool calls")
            await self._call_llm(tool_choice="none", response_format=response_format)

        output = response_format.model_validate_json(
            cast(str, self.memory.messages[-1].get("content"))
        )
        return output.text_response

    async def _call_llm(
        self, *, tool_choice: Any, response_format: type[BaseChatResponse]
    ) -> None:
        tools = await self.get_tools()
        system_prompt = await self.get_system_prompt()
        try:
            response = self._client.chat(
                self.memory.build_messages(system_prompt),
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )
        except BadRequestError:
            logger.exception("LLM call failed; shrinking memory and retrying")
            self.memory.shrink_messages_to_fit_token_limit(True)
            response = self._client.chat(
                self.memory.build_messages(system_prompt),
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )

        msg = response.choices[0].message
        assistant_dict: dict[str, Any] = {
            "role": "assistant",
            "content": getattr(msg, "content", None),
        }
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            assistant_dict["tool_calls"] = []
            for tc in tool_calls:
                fn = getattr(tc, "function", None)
                assistant_dict["tool_calls"].append(
                    {
                        "id": getattr(tc, "id", None),
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": getattr(fn, "name", None),
                            "arguments": getattr(fn, "arguments", None),
                        },
                    }
                )
        self.memory.add_assistant(assistant_dict)

    async def _add_tool_results_to_memory(
        self, assistant_message: dict[str, Any]
    ) -> None:
        tool_calls = assistant_message.get("tool_calls") or []
        tool_call_list = []
        tool_call_id_list = []
        async with MCPClient() as mcp_client:
            for tool_call in tool_calls:
                fn = tool_call.get("function") or {}
                name = fn.get("name")
                assert name
                arguments = fn.get("arguments") or "{}"
                try:
                    args_dict = (
                        json.loads(arguments)
                        if isinstance(arguments, str)
                        else arguments
                    )
                except json.JSONDecodeError:
                    args_dict = {}
                logger.info(f"Calling tool: {name} with args: {args_dict}")
                tool_call_list.append(mcp_client.call(name, args=args_dict))
                tool_call_id_list.append(tool_call.get("id"))

            for result, tool_call_id in zip(
                await asyncio.gather(*tool_call_list), tool_call_id_list
            ):
                # logger.info(f"Tool call result: {result}")
                self.memory.add_tool_result(tool_call_id or "", result=str(result))

    def _replace_variables_in_prompt(self, content: str) -> str:
        """Replace variables in the prompt based on agent_config.replace_variables.

        Loads variables_to_replace_in_prompt from <agent_folder_path>/replacement_method.py if available.
        If a replace_variables value is "...", substitute from variables_to_replace_in_prompt.
        Otherwise, use the literal value from agent_config.
        """
        dynamic_variables: dict[str, Any] = {}
        try:
            module_name = f"agent_replacement_method_{hash(self.agent_folder_path)}"
            spec = importlib.util.spec_from_file_location(  # use explicit util
                module_name, str(self.agent_folder_path / "replacement_method.py")
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)  # use explicit util
                spec.loader.exec_module(module)
                variables_to_replace_in_prompt_func = getattr(
                    module, "variables_to_replace_in_prompt", None
                )
                if callable(variables_to_replace_in_prompt_func):
                    dynamic_variables = variables_to_replace_in_prompt_func(self) or {}
        except (FileNotFoundError, ImportError):
            pass

        replace_vars = (
            getattr(self.agent_settings.agent_config, "replace_variables", None) or {}
        )
        for key, value in replace_vars.items():
            try:
                final_val = (
                    dynamic_variables[key] if str(value).strip() == "..." else value
                )
            except KeyError:
                raise ValueError(
                    f"replace_variables has '...' for key '{key}' "
                    "but no dynamic value was provided by replacement_method.py"
                )
            content = content.replace(f"{{{key}}}", str(final_val))

        return content
