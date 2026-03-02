from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.config.settings import AgentConfig


def build_chat_model(config: AgentConfig) -> BaseChatModel:
    """Build a LangChain chat model from AgentConfig without changing YAML contract."""
    model_name = config.model
    provider, _, model_id = model_name.partition("/")
    resolved_model = model_id or model_name

    common_kwargs = {
        "model": resolved_model,
        "temperature": config.temperature,
        "timeout": config.timeout,
        "max_tokens": config.max_tokens,
    }

    if provider in {"openai", "azure"}:
        openai_kwargs: dict[str, object] = {
            **common_kwargs,
            "api_key": config.api_key,
        }
        if config.endpoint:
            openai_kwargs["base_url"] = config.endpoint
        return ChatOpenAI(**openai_kwargs)

    if provider == "anthropic":
        return ChatAnthropic(
            **common_kwargs,
            api_key=config.api_key,
            base_url=config.endpoint or None,
        )

    raise ValueError(f"Unsupported model provider prefix in AgentConfig.model: {model_name}")
