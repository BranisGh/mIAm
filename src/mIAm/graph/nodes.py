from typing import List, Optional, Dict, Any
import os

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage

from pydantic import BaseModel

from mIAm.graph.llm import LLM
from mIAm.graph.state import State
from mIAm.graph.trimmer import TRIMMER
from mIAm.graph.prompts import INFO_CHAIN_SYSTEM_PROMPT, GENERATOR_SYSTEM_PROMPT




def info_chain(state: State) -> State:
    """
    Handles recipe-related queries using structured response formatting.

    Args:
        state (dict): The current conversation state.

    Returns:
        dict: Updated state containing AI response.
    """
    class RecipeInstructions(BaseModel):
        """
        Structured format for generating a recipe response.
        Ensures consistent and structured output.
        """
        recipe_name: str
        dish_type: str
        dietary_preferences: List[str]
        ingredients: List[str]
        time_constraints: str
        special_instructions: List[str]
        formatted_query: str
    
    trimmed_messages = TRIMMER.invoke(state["messages"])
    messages = [SystemMessage(content=INFO_CHAIN_SYSTEM_PROMPT)] + trimmed_messages
    llm_with_tool = LLM.bind_tools([RecipeInstructions])
    response = llm_with_tool.invoke(messages)
    return {"messages": [response]}


def generator(state: State) -> State:
    """
    Generates a response using LLM by extracting relevant tool calls.

    Args:
        state (dict): The current conversation state.

    Returns:
        dict: Updated state with generated response.
    """
    trimmed_messages = TRIMMER.invoke(state["messages"])
    tool_call: Optional[Dict[str, Any]] = None
    other_msgs = []

    for m in trimmed_messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            tool_call = m.tool_calls[0]["args"]
        elif isinstance(m, ToolMessage):
            continue
        elif tool_call is not None:
            other_msgs.append(m)
    
    formatted_query = tool_call.get("formatted_query", "Unknown Query")
    system_prompt = GENERATOR_SYSTEM_PROMPT.format(requirements=tool_call, formatted_query=formatted_query)
    
    response = LLM.invoke([SystemMessage(content=system_prompt)] + other_msgs)
    return {"messages": [response]}
