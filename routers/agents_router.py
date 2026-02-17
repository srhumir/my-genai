import os
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.initiator import load_agent_paths
from src.agents_library.memory import (
    cleanup_expired_memory,
    get_or_create_memory,
    memory_lock,
    memory_store,
)
from src.agents_library.response_types import AgentRequest, AgentResponse
from src.config.settings import settings

router = APIRouter()


@router.delete("/memory/{agent_key}/{correlation_id}")
def delete_memory(agent_key: str, correlation_id: str) -> dict[str, str]:
    with memory_lock:
        if agent_key in memory_store and correlation_id in memory_store[agent_key]:
            del memory_store[agent_key][correlation_id]
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Memory not found")


agent_paths = load_agent_paths()


def get_agent_key(path_of_agent: Path) -> str:
    return os.path.split(path_of_agent)[1]


def _create_agent_endpoint(
    _agent_path: Path,
) -> Callable[[AgentRequest], Coroutine[Any, Any, AgentResponse]]:
    _agent_key = get_agent_key(agent_path)

    async def agent_endpoint(request: AgentRequest) -> AgentResponse:
        cleanup_expired_memory()
        memory, cid = get_or_create_memory(_agent_key, request.correlation_id)
        session_config = ChatSessionConfig(
            bot_user_name="TestBot",
            session_id="session_123",
            topic_id="topic_abc",
        )
        agent = BaseAgent(
            settings=settings,
            session_config=session_config,
            memory=memory,
            agent_folder_path=_agent_path,
        )
        response = await agent.prepare_response(request.query)
        return AgentResponse(response=response, correlation_id=cid)

    return agent_endpoint


for agent_path in agent_paths:
    agent_key = get_agent_key(agent_path)
    route = f"/{agent_key}"
    router.add_api_route(
        route,
        _create_agent_endpoint(agent_path),
        methods=["POST"],
        response_model=AgentResponse,
    )
