import chainlit as cl

from src.agents_library.base import BaseAgent, ChatSessionConfig
from src.agents_library.memory import ConversationMemory
from src.config.settings import settings

AGENT_FOLDER_PATH = "src/agents_library/agents/$AGENT"


@cl.on_chat_start
async def on_chat_start() -> None:
    session = ChatSessionConfig(
        bot_user_name="Assistant",
        session_id="session",
        topic_id="default",
    )
    memory = ConversationMemory()
    agent = BaseAgent(
        settings=settings, session_config=session, memory=memory, agent_folder_path=AGENT_FOLDER_PATH
    )
    cl.user_session.set("agent", agent)

    await cl.Message("Hello! How can I assist you today?").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    agent = cl.user_session.get("agent")
    if agent is None:
        await cl.Message("Session not initialized. Please refresh the chat.").send()
        return

    reply = await agent.prepare_response(message.content or "")
    await cl.Message(content=reply).send()
