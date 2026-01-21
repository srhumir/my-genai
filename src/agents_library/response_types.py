from pydantic import BaseModel


class BaseChatResponse(BaseModel):
    """The base type to pass to ChatClient.chat as response_format.

    It is the default and every other chat is format has to be inherited form this.
    """

    text_response: str
