from __future__ import annotations

from typing import Any

import litellm
from pydantic import BaseModel

from src.agents_library.response_types import BaseChatResponse
from src.config.settings import Settings, settings


class ChatClient:
    """Thin wrapper around LiteLLM to call chat completions using app settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._config = settings.agent_config

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[Any] | None = None,
        tool_choice: Any | None = "auto",
        response_format: type[BaseModel] = BaseChatResponse,
    ) -> litellm.ModelResponse:
        """Call the underlying model and return the raw LiteLLM response.

        Args:
            messages: OpenAI-compatible chat message list.
            tools: Optional OpenAI-compatible tools list.
            tool_choice: Tool choice option (e.g., "auto", "none", or a specific tool spec).
            response_format: Pydantic model to parse the response into.

        Returns:
            The LiteLLM ModelResponse object (OpenAI-style).
        """
        if not isinstance(response_format, type(BaseChatResponse)):
            raise ValueError(
                "response_format is supposed to be inherited from BaseChatResponse"
            )
        cfg = self._config
        resp = litellm.completion(
            model=cfg.model,
            messages=messages,
            api_key=cfg.api_key,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            stop=cfg.stop,
            stream=cfg.stream,
            timeout=cfg.timeout,
            tools=tools,
            tool_choice=tool_choice if tools else None,
            api_base=cfg.endpoint or None,
            response_format=response_format,
        )
        return resp


if __name__ == "__main__":
    agent_config = settings.agent_config
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "List 5 important events in the XIX century"},
    ]
    client = ChatClient(settings)
    resp = client.chat(messages)

    print(resp)
