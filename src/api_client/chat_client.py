from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel

from src.agents_library.response_types import BaseChatResponse
from src.api_client.langchain_adapter import build_chat_model
from src.config.settings import Settings


class ChatClient:
    """Run chat interactions through a LangGraph tool loop.

    The graph contains:
      - an ``agent`` node that calls the configured chat model.
      - an optional ``tools`` node that executes LangChain tools for tool calls.

    Conversation history is persisted by thread ID using LangGraph's in-memory
    checkpointer so callers can continue multi-turn conversations.
    """

    _checkpointer = MemorySaver()

    def __init__(self, settings: Settings) -> None:
        self._config = settings.agent_config

    async def chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        thread_id: str,
        tools: list[Any] | None = None,
        response_format: type[BaseModel] = BaseChatResponse,
    ) -> BaseModel:
        """Generate a structured chat response using the LangGraph runtime.

        Args:
            system_prompt: System prompt text for the conversation.
            user_message: Latest user message for this turn.
            thread_id: Conversation ID used by LangGraph checkpointer memory.
            tools: Optional LangChain-compatible tools to bind to the model.
            response_format: Pydantic response schema inheriting BaseChatResponse.

        Returns:
            A validated pydantic model instance matching ``response_format``.
        """
        if not issubclass(response_format, BaseChatResponse):
            raise ValueError(
                "response_format is supposed to be inherited from BaseChatResponse"
            )

        chat_model = build_chat_model(self._config)
        tool_list = tools or []
        model_with_tools = chat_model.bind_tools(tool_list) if tool_list else chat_model

        graph_builder = StateGraph(MessagesState)

        async def agent_node(state: MessagesState) -> dict[str, list[Any]]:
            model_response = await model_with_tools.ainvoke(state["messages"])
            return {"messages": [model_response]}

        graph_builder.add_node("agent", agent_node)
        if tool_list:
            graph_builder.add_node("tools", ToolNode(tool_list))
        graph_builder.set_entry_point("agent")
        if tool_list:
            graph_builder.add_conditional_edges(
                "agent",
                tools_condition,
                {"tools": "tools", END: END},
            )
            graph_builder.add_edge("tools", "agent")
        else:
            graph_builder.add_edge("agent", END)

        app = graph_builder.compile(checkpointer=self._checkpointer)
        graph_result = await app.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        final_model = chat_model.with_structured_output(response_format)
        return await final_model.ainvoke(graph_result["messages"])
