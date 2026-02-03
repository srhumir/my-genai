import os
from dataclasses import field
from typing import Literal

from dotenv import load_dotenv
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
    name: str = "Default Agent"
    description: str = "An AI agent powered by GPT-5.2"
    replace_variables: dict[str, str] = field(default_factory=dict)
    endpoint: str = ""
    model: str = "openai/gpt-5.2"
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
    agent_config: AgentConfig = field(default_factory=AgentConfig)


settings = Settings()
