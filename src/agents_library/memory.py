import threading
import time
import uuid
from logging import getLogger
from typing import Any

logger = getLogger(__name__)

# Global memory store: {agent_key: {correlation_id: (ConversationMemory, last_used_timestamp)}}
memory_store: dict[str, dict[str, tuple["ConversationMemory", float]]] = {}
memory_lock = threading.Lock()
MEMORY_RETENTION_SECONDS = 3600


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


def get_or_create_memory(
    agent_key: str, correlation_id: str | None
) -> tuple[ConversationMemory, str]:
    now = time.time()
    with memory_lock:
        if agent_key not in memory_store:
            memory_store[agent_key] = {}
        if correlation_id and correlation_id in memory_store[agent_key]:
            memory, _ = memory_store[agent_key][correlation_id]
            memory_store[agent_key][correlation_id] = (memory, now)
            return memory, correlation_id

        new_id = correlation_id or str(uuid.uuid4())
        memory = ConversationMemory()
        memory_store[agent_key][new_id] = (memory, now)
        return memory, new_id


def cleanup_expired_memory() -> None:
    now = time.time()
    with memory_lock:
        for agent_key in list(memory_store.keys()):
            for cid in list(memory_store[agent_key].keys()):
                _, last_used = memory_store[agent_key][cid]
                if now - last_used > MEMORY_RETENTION_SECONDS:
                    del memory_store[agent_key][cid]
