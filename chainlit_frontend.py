from pathlib import Path
from urllib.parse import parse_qs, urlparse

import chainlit as cl

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.memory import ConversationMemory
from src.config.settings import settings

AGENT_FOLDER_BASE_PATH = Path("src/agents_library/agents")


@cl.on_chat_start
async def on_chat_start() -> None:
    url = cl.context.session.environ["HTTP_REFERER"]
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    agent_name = get_param(query_params, "agent")
    if not agent_name:
        await cl.Message(
            "No agent specified. Please provide an agent query parameter in the URL."
        ).send()  # type: ignore[no-untyped-call]
        return
    session = ChatSessionConfig(
        bot_user_name="Assistant",
        session_id="session",
        topic_id="default",
    )
    memory = ConversationMemory()
    agent = BaseAgent(
        settings=settings,
        session_config=session,
        memory=memory,
        agent_folder_path=(AGENT_FOLDER_BASE_PATH / agent_name),
    )
    cl.user_session.set("agent", agent)  # type: ignore[no-untyped-call]

    await cl.Message(
        f"Hello! I am here to {agent.agent_settings.agent_config.description} How can I assist you today?"
    ).send()  # type: ignore[no-untyped-call]


@cl.on_message
async def on_message(message: cl.Message) -> None:
    agent = cl.user_session.get("agent")  # type: ignore[no-untyped-call]
    if agent is None:
        await cl.Message("Session not initialized. Please refresh the chat.").send()  # type: ignore[no-untyped-call]
        return

    reply = await agent.prepare_response(message.content or "")
    await cl.Message(content=reply).send()  # type: ignore[no-untyped-call]


def get_param(query_params: dict[str, list[str]], key: str) -> str | None:
    """Helper function to get a single value from query parameters."""
    return query_params.get(key, [None])[0]
