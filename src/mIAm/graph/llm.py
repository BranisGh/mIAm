from langchain_openai import ChatOpenAI
import os

LLM = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)
