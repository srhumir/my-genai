from pydantic import BaseModel


class AgentRequest(BaseModel):
    query: str
    correlation_id: str | None = None


class AgentResponse(BaseModel):
    response: str
    correlation_id: str


class BaseChatResponse(BaseModel):
    """The base type to pass to ChatClient.chat as response_format.

    It is the default and every other chat is format has to be inherited form this.
    """

    text_response: str
