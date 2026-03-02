import importlib.util
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

from async_lru import alru_cache

from src.agents_library import build_agent_settings
from src.agents_library.response_types import BaseChatResponse
from src.api_client.chat_client import ChatClient
from src.config.settings import Settings
from src.mcp_client.client import MCPClient
from src.mcp_client.langgraph_tools import openai_tools_to_langchain

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
        agent_folder_path: str | Path,
    ) -> None:
        self.agent_folder_path = Path(agent_folder_path)
        self.agent_settings = build_agent_settings(
            settings, self.agent_folder_path / "agent_config.yaml"
        )
        self.session_config = session_config
        self._client = ChatClient(self.agent_settings)

    async def get_system_prompt(self) -> str:
        tool_description_list = [
            f"* {tool['function']['name']}: {tool['function']['description'].split(chr(10))[0]}"
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
    async def get_tools(self) -> list[dict[str, Any]]:
        if self.agent_settings.agent_config.my_mcp_tools is None:
            return []

        async with MCPClient() as mcp_client:
            all_mcp_tools = await mcp_client.get_openai_tools()

        allowed = set(self.agent_settings.agent_config.my_mcp_tools or [])
        return [dict(t) for t in all_mcp_tools if t["function"]["name"] in allowed]

    async def prepare_response(
        self, message: str, response_format: type[BaseChatResponse] = BaseChatResponse
    ) -> str:
        tools = openai_tools_to_langchain(await self.get_tools())
        system_prompt = await self.get_system_prompt()
        output = await self._client.chat(
            system_prompt=system_prompt,
            user_message=message,
            tools=tools,
            thread_id=self.session_config.session_id,
            response_format=response_format,
        )
        validated = response_format.model_validate(output)
        return validated.text_response

    @alru_cache
    async def get_initial_action_prompts(self) -> dict[str, str]:
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

    def _replace_variables_in_prompt(self, content: str) -> str:
        dynamic_variables: dict[str, Any] = {}
        try:
            module_name = f"agent_replacement_method_{hash(self.agent_folder_path)}"
            spec = importlib.util.spec_from_file_location(
                module_name, str(self.agent_folder_path / "replacement_method.py")
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
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
