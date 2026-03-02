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
    """Run chat interactions through a LangGraph tool loop."""

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
