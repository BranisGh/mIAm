import streamlit as st
import asyncio
import os
from langchain_core.messages import HumanMessage, AIMessage

# Import your workflow components
# Assuming these modules are properly installed/available
from mIAm.graph.workflow import workflow

# Page configuration
st.set_page_config(page_title="Recipe Assistant", page_icon="🍳")

# Initialize session state for conversation and thread ID
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "thread_id" not in st.session_state:
    # Create a unique thread ID for this session
    import uuid
    st.session_state.thread_id = str(uuid.uuid4())

# App header
st.title("🍳 Recipe Assistant")
st.markdown("Let me help you create delicious recipes! Tell me what ingredients you have or what dish you'd like to make.")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Setup the workflow graph (without database integration for now)
@st.cache_resource
def get_workflow():
    return workflow.compile()

# User input
user_input = st.chat_input("What would you like to cook today?")

# Process user input
if user_input:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Set up and call the LangGraph workflow
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Get the compiled graph
        graph = get_workflow()
        
        # Define the config for this session
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        # Process the input through the workflow
        try:
            # In Streamlit, we need to handle async operations differently
            # This is a synchronous version for simplicity
            # We'll use the stream method to get updates
            for output in graph.stream(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=config, 
                stream_mode="updates"
            ):
                # Get the last message from the output
                last_message = next(iter(output.values()))["messages"][-1]
                
                # Extract the content
                if hasattr(last_message, "content") and last_message.content:
                    content = last_message.content
                    # Update the display with new content
                    full_response = content
                    message_placeholder.markdown(full_response)
            
            # Ensure the final response is shown
            if full_response:
                message_placeholder.markdown(full_response)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        except Exception as e:
            error_message = f"Error processing your request: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})