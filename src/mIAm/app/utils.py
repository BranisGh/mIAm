import os
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
import streamlit as st


async def load_chat_history(thread_id):
    DB_URI = f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}" \
             f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}" \
             f"?sslmode={os.getenv('PSQL_SSLMODE')}"
    
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    
    try:
        async with AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            
            config = {"configurable": {"thread_id": str(thread_id)}}
            checkpoint = await checkpointer.aget(config)
            
            if checkpoint and "channel_values" in checkpoint and "messages" in checkpoint["channel_values"]:
                messages = checkpoint["channel_values"]["messages"]
                
                # Conversion des messages LangChain en format compatible avec notre interface
                chat_history = []
                for msg in messages:
                    if hasattr(msg, "content") and msg.content:
                        if isinstance(msg, HumanMessage):
                            chat_history.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            chat_history.append({"role": "assistant", "content": msg.content})
                
                return chat_history
            
            return []
    except Exception as e:
        st.error(f"Error loading chat history: {str(e)}")
        return []

# Modifiez la fonction select_thread pour charger l'historique des messages
def select_thread(thread_id):
    st.session_state.thread_id = thread_id
    
    # Charger l'historique des messages de façon asynchrone
    st.session_state.chat_history = asyncio.run(load_chat_history(thread_id))
    
    st.session_state.current_view = "chat"