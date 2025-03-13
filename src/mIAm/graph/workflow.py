from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END
from langgraph.graph import StateGraph, START
from mIAm.graph.state import State
from mIAm.graph.nodes import info_chain, generator


def get_state(state):
    messages = state["messages"]
    if isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "add_tool_message"
    elif not isinstance(messages[-1], HumanMessage):
        return END
    return "info"



workflow = StateGraph(State)
workflow.add_node("info_chain", info_chain)
workflow.add_node("generator", generator)


@workflow.add_node
def add_tool_message(state: State):
    return {
        "messages": [
            ToolMessage(
                content="Response generated using RecipeInstructions tool.",
                tool_call_id=state["messages"][-1].tool_calls[0]["id"],
            )
        ]
    }


workflow.add_conditional_edges("info_chain", get_state, ["add_tool_message", "info_chain", END])
workflow.add_edge("add_tool_message", "generator")
workflow.add_edge("generator", END)
workflow.add_edge(START, "info_chain")
