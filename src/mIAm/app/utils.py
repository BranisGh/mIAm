import os
import asyncio
import streamlit as st
from typing import List, Dict
import psycopg
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from mIAm import setup_logger
import logging

logger = setup_logger(console_logging_enabled=True, log_level=logging.INFO)

load_dotenv()


async def load_chat_history(thread_id):
    DB_URI = f"postgresql://postgres.fagpasxtuxuwhbkkeowy:{os.getenv('SUPABASE_DB_PASSWORD')}" \
             f"@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": None,
    }
    
    # Use async context manager for the connection pool
    async with AsyncConnectionPool(
        conninfo=DB_URI, 
        max_size=20, 
        kwargs=connection_kwargs
    ) as pool:
        try:
            # Use a connection from the pool
            async with pool.connection() as conn:
                checkpointer = AsyncPostgresSaver(conn)
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
        
        except psycopg.errors.DuplicatePreparedStatement:
            # Log the specific error, but continue
            logger.warning("Duplicate prepared statement detected. This is usually harmless.")
            return []
        except Exception as e:
            logger.error(f"Error loading chat history: {str(e)}")
            st.error(f"Error loading chat history: {str(e)}")
            return []

        
def select_thread(thread_id):
    st.session_state.thread_id = thread_id

    # Loading chat history
    st.session_state.chat_history = asyncio.run(load_chat_history(thread_id))

    st.session_state.current_view = "chat"