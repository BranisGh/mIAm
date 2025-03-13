from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI


TRIMMER = trim_messages(
    strategy="last",
    token_counter=ChatOpenAI(model="gpt-4o"),
    max_tokens=1000,
    start_on="human",
    end_on=("human", "tool"),
    include_system=True,
    allow_partial=False,
)
