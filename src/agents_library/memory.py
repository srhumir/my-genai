import time
from logging import getLogger
from typing import Any

logger = getLogger(__name__)


class ConversationMemory:
    def __init__(self, hard_limit_tokens: int = 1_000):
        self.hard_limit_tokens = hard_limit_tokens
        self.messages: list[dict[str, Any]] = []
        self.summaries: list[str] = []
        self.created_at: float = time.time()

    def add_user(self, text: str) -> None:
        self.shrink_messages_to_fit_token_limit(False)
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call_id,
            }
        )

    def build_messages(self, system_prompt: str) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for s in self.summaries:
            msgs.append({"role": "assistant", "content": f"(summary) {s}"})
        return msgs + self.messages

    def incorporate_summary(self, summary_text: str, drop_until: int) -> None:
        """Save a model-generated abstract and prune older turns up to index drop_until."""
        self.summaries.append(summary_text)
        self.messages = self.messages[drop_until:]

    def clear(self) -> None:
        self.messages.clear()
        self.summaries.clear()

    def shrink_messages_to_fit_token_limit(self, force_shrink: bool) -> None:
        if (self._count_tokens() > self.hard_limit_tokens) or force_shrink:
            logger.info(f"Number of tokens before shrinking: {len(self.messages)}")
            self._remove_tool_calls_from_messages_until_tokens_below_limit(force_shrink)
            logger.info(f"Number of tokens after shrinking: {len(self.messages)}")

    def _remove_tool_calls_from_messages_until_tokens_below_limit(
        self, force_shrink: bool
    ) -> None:
        """Remove tool call messages from the start of the message list until the token count is below the hard limit."""
        logger.info(
            "Token limit exceeded, removing tool call messages to fit within limit."
        )
        while (self._count_tokens() > self.hard_limit_tokens) or force_shrink:
            for i, msg in enumerate(self.messages[:-1]):
                if msg.get("role") == "tool":
                    del self.messages[i]
                    break
            else:
                break

    def _count_tokens(self) -> int:
        total_tokens = 0
        for msg in self.messages:
            content = msg.get("content")
            if isinstance(content, str) and content:
                total_tokens += len(content.split())
        return total_tokens
