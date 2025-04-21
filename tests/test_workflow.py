import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import json

# Import the modules to test
from mIAm.graph.workflow import workflow, get_state
from mIAm.graph.nodes import info_chain, generator
from mIAm.graph.state import State
from langgraph.graph import END



@pytest.fixture
def mock_trimmer():
    with patch("mIAm.graph.nodes.TRIMMER") as mock:
      async_mock = AsyncMock()
      async_mock.ainvoke = AsyncMock(side_effect=lambda x: x)
      mock.return_value = async_mock
      mock.ainvoke = async_mock.ainvoke
      yield mock

@pytest.fixture
def mock_llm():
    """Mock the LLM."""
    with patch('mIAm.graph.nodes.LLM') as mock:
        # Create a mock that can be configured for different test cases
        llm_mock = AsyncMock()
        
        # Default response for normal queries
        normal_response = AIMessage(content="This is a test response from the LLM.")
        llm_mock.ainvoke = AsyncMock(return_value=normal_response)
        
        # Configure bind_tools to return a mock that also has ainvoke method
        bind_tools_mock = AsyncMock()
        bind_tools_mock.ainvoke = AsyncMock(return_value=normal_response)
        mock.bind_tools.return_value = bind_tools_mock
        
        # Return a configureable mock
        yield mock, llm_mock


class TestWorkflowNodes:

  def test_info_chain_basic(self, mock_trimmer, mock_llm):
    """Test the info_chain node with a basic query."""
    mock_llm_class, mock_llm_instance = mock_llm
    

    state = {"messages": [HumanMessage(content="I need a pasta recipe")]}
    
    # Call the function
    import asyncio
    result = asyncio.run(info_chain(state))
    
    # Verify the trimmer was called
    mock_trimmer.ainvoke.assert_called_once_with(state["messages"])
    
    # Verify bind_tools was called with RecipeInstructions
    mock_llm_class.bind_tools.assert_called_once()
    
    # Check that we got a response back
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)


  def test_info_chain_with_tool_call(self, mock_trimmer, mock_llm):
    """Test the info_chain node with tools."""
    mock_llm_class, mock_llm_instance = mock_llm
    
    tool_call_response = AIMessage(
       content="",
       additional_kwargs={
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "RecipeInstructions",
                    "arguments": "..."
                }
            }
        ]
    }
    )

    bind_tools_mock = mock_llm_class.bind_tools.return_value

    bind_tools_mock.ainvoke = AsyncMock(return_value=tool_call_response)


    state = {"messages": [HumanMessage(content="I need a pasta recipe")]}


    import asyncio
    result = asyncio.run(info_chain(state))

    mock_trimmer.ainvoke.assert_called_once_with(state["messages"])
        
    mock_llm_class.bind_tools.assert_called_once()

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert hasattr(result["messages"][0], "additional_kwargs")
    assert "tool_calls" in result["messages"][0].additional_kwargs
    assert result["messages"][0].additional_kwargs["tool_calls"][0]["id"] == "call_123"

