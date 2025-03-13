from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
