import os
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

async def load_chat_history(thread_id):
    DB_URI = f"postgresql://postgres.fagpasxtuxuwhbkkeowy:{os.getenv('SUPABASE_DB_PASSWORD')}" \
             f"@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }

    # Create the pool without opening it immediately
    pool = AsyncConnectionPool(
        conninfo=DB_URI,
        max_size=20,
        kwargs=connection_kwargs
    )

    try:
        # Explicitly open the pool
        await pool.open()

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        config = {"configurable": {"thread_id": str(thread_id)}}
        checkpoint = await checkpointer.aget(config)

        if checkpoint and "channel_values" in checkpoint and "messages" in checkpoint["channel_values"]:
            messages = checkpoint["channel_values"]["messages"]

            # Converting LangChain messages to a format compatible with our interface
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
    finally:
        # Ensure the pool is closed after use
        await pool.close()

def select_thread(thread_id):
    st.session_state.thread_id = thread_id

    # Loading chat history
    st.session_state.chat_history = asyncio.run(load_chat_history(thread_id))

    st.session_state.current_view = "chat"