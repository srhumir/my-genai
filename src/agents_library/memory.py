import threading
import time
import uuid

memory_store: dict[str, dict[str, float]] = {}
memory_lock = threading.Lock()
MEMORY_RETENTION_SECONDS = 3600


def get_or_create_memory(agent_key: str, correlation_id: str | None) -> str:
    now = time.time()
    with memory_lock:
        if agent_key not in memory_store:
            memory_store[agent_key] = {}

        if correlation_id and correlation_id in memory_store[agent_key]:
            memory_store[agent_key][correlation_id] = now
            return correlation_id

        new_id = correlation_id or str(uuid.uuid4())
        memory_store[agent_key][new_id] = now
        return new_id


def cleanup_expired_memory() -> None:
    now = time.time()
    with memory_lock:
        for agent_key in list(memory_store.keys()):
            for cid in list(memory_store[agent_key].keys()):
                last_used = memory_store[agent_key][cid]
                if now - last_used > MEMORY_RETENTION_SECONDS:
                    del memory_store[agent_key][cid]
