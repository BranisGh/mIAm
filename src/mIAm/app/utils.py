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
import warnings

logger = setup_logger(console_logging_enabled=True, log_level=logging.INFO)
load_dotenv()

async def load_chat_history(thread_id):
    """
    Load chat history with improved async pool handling.
    """
    # Suppress the specific deprecation warning
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                             message="opening the async pool AsyncConnectionPool in the constructor is deprecated")
    
    # Construct connection URI
    # DB_URI = f"postgresql://postgres.fagpasxtuxuwhbkkeowy:{os.getenv('SUPABASE_DB_PASSWORD')}" \
    #          f"@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    DB_URI = f"postgresql://postgres.fagpasxtuxuwhbkkeowy:{os.getenv('SUPABASE_DB_PASSWORD')}@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": None,  # Disable automatic prepared statements
    }

    # Use async context manager for the connection pool
    try:
        async with AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs
        ) as pool:
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

    except psycopg.errors.DuplicatePreparedStatement as dps:
        # Log the specific error with more context
        logger.warning(f"Duplicate prepared statement detected: {str(dps)}")
        return []
    
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}")
        st.error(f"Error loading chat history: {str(e)}")
        return []

async def load_thread_history(thread_id: str) -> List[Dict[str, str]]:
    """Load chat history for a thread."""
    try:
        return await load_chat_history(thread_id)
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}")
        st.error("Failed to load chat history. Please try refreshing the page.")
        return []