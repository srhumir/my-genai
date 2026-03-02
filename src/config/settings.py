import os
from dataclasses import field
from typing import Literal

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ChatBotConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    pass


class MCPClientConfig(ChatBotConfig):
    mcp_server_url: str = "http://localhost:8001/mcp"


class AgentConfig(ChatBotConfig):
    """AgentConfig defines the runtime settings for an agent and maps directly to agent_config.yaml.

    Required
    - name: Human-friendly agent name.
    - description: Short purpose of the agent.
    - model: provider/model id (e.g., "openai/gpt-4o", "anthropic/claude-3-5-sonnet", "azure/<deployment>").

    Optional (common)
    - endpoint: Custom API base URL for the model (Azure/OpenAI proxy). Default: "".
    - max_tokens: Upper bound for generated tokens. Default: 1000.
    - temperature: Sampling temperature. Default: 0.3.
    - top_p: Nucleus sampling. Default: 0.95.
    - frequency_penalty: Penalize token repetition. Default: 0.
    - presence_penalty: Encourage new tokens. Default: 0.
    - stop: Stop sequence string. Default: None.
    - stream: Enable streaming. Default: False.
    - timeout: Request timeout in seconds. Default: 60.

    Tools and collaboration
    - my_mcp_tools: List of MCP tool names this agent is allowed to use from the mcp server provided in the same repo.
       If None/empty, no tools will be used.
    - open_mcp_tools: List of publicly availabe MCP tools this agent can call.

    Search augmentation
    - search_context_size: one of {"low", "medium", "high"}.

    Prompt templating
    - replace_variables: key/value pairs to interpolate in system_prompt.md.
    """

    name: str = MISSING
    description: str = MISSING
    replace_variables: dict[str, str] = field(default_factory=dict)
    endpoint: str = ""
    model: str = MISSING
    max_tokens: int = 1000
    temperature: float = 0.3
    top_p: float = 0.95
    frequency_penalty: float = 0
    presence_penalty: float = 0
    stop: str | None = None
    stream: bool = False
    timeout: int = 60
    my_mcp_tools: list[str] | None = None
    search_context_size: Literal["low", "medium", "high"] | None = None
    open_mcp_tools: list[str] | None = None

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, value: str) -> str:
        """Validate model format as <provider>/<model-name>."""
        provider, sep, model_name = value.partition("/")
        if not sep or not provider or not model_name:
            raise ValueError(
                "model must use '<provider>/<model-name>' format (e.g. openai/gpt-4o)"
            )

        allowed_providers = {"openai", "azure", "anthropic", "google"}
        if provider not in allowed_providers:
            raise ValueError(
                f"model provider must be one of {sorted(allowed_providers)}; got '{provider}'"
            )
        return value

    @property
    def api_key(self) -> str | None:
        if self.model.startswith("openai"):
            return os.getenv("OPEN_API_KEY")
        if self.model.startswith("azure"):
            return os.getenv("AZURE_API_KEY")
        if self.model.startswith("anthropic"):
            return os.getenv("ANTHROPIC_API_KEY")
        if self.model.startswith("google"):
            return os.getenv("GOOGLE_API_KEY")
        return None


class Settings(ChatBotConfig):
    MAX_CACHE_SIZE: int = 128
    mcp_server_config: MCPClientConfig = field(default_factory=MCPClientConfig)
    agent_config: AgentConfig = field(
        default_factory=lambda: AgentConfig(
            name="default-agent",
            description="default-agent",
            model="openai/gpt-4o",
        )
    )


settings = Settings()
