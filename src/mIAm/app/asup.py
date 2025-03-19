import streamlit as st
import asyncio
from uuid import uuid4
from datetime import date
import os
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from mIAm.graph.prompts import CHAT_PROMPT
from mIAm.app.utils import load_chat_history
import time
from mIAm.postgres_db.exceptions import (
    InvalidAuthenticationDataError,
    InvalidRegestrationDataError,
    UserNotFoundError,
    InvalidPasswordError
)

# Load environment variables
load_dotenv()

# Initialize OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets.get("OPENAI_API_KEY", "")

# Import mIAm modules after setting API key
from mIAm.graph.workflow import workflow
from mIAm.postgres_db.postgres_db_manager import PostgresDBManager

# Page configuration
st.set_page_config(
    page_title="mIAm",
    page_icon="🍲",
    initial_sidebar_state="expanded",
)

# Database connection string
def get_db_uri() -> str:
    """Generate PostgreSQL connection URI from environment variables."""
    return (
        f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}"
        f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}"
        f"?sslmode={os.getenv('PSQL_SSLMODE')}"
    )

# Database Configuration
@st.cache_resource
def get_db_manager() -> PostgresDBManager:
    """Get database manager instance (cached)."""
    return PostgresDBManager(
        conn_string=get_db_uri(),
        initialize_db=True
    )

# Session state initialization
def init_session_state() -> None:
    """Initialize session state variables."""
    defaults = {
        "authenticated": False,
        "user_id": None,
        "user_profile": None,
        "thread_id": None,
        "chat_history": [],
        "current_view": "login",
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY", ""))
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Navigation helper
def navigate_to(view: str) -> None:
    """Navigate to a specific view."""
    st.session_state.current_view = view

# User authentication
def login_user() -> None:
    """Authenticate user and set session state."""
    try:
        db_manager = get_db_manager()
        user = db_manager.authenticate_user(
            email=st.session_state.email,
            password=st.session_state.password
        )
        st.session_state.authenticated = True
        st.session_state.user_id = user["id"]
        st.session_state.user_profile = db_manager.get_user_profile(user_id=user["id"])
        st.session_state.chat_history = []
        st.success("Login successful!")
        navigate_to("chat")
    except (InvalidAuthenticationDataError, UserNotFoundError, InvalidPasswordError) as e:
        st.error(str(e))
        if hasattr(e, 'errors'):
            for error in e.errors:
                st.error(error["error"])
    except Exception as e:
        st.error(f"Error logging in: {str(e)}")

def render_login_view() -> None:
    """Render the login view."""
    st.markdown(
        """
        <h2 style='text-align: center;'>🍲 Welcome to mIAm 🍝</h2>
        <p style='text-align: center; color: gray;'>Please enter your credentials to continue.</p>
        """, 
        unsafe_allow_html=True
    )
    
    with st.form("login_form", clear_on_submit=False):
        st.markdown("### 🔑 Sign In")
        
        st.text_input("📧 Email *", key="email", placeholder="Enter your email", help="Your registered email")
        st.text_input("🔒 Password *", key="password", type="password", placeholder="Enter your password", help="Your secure password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            sign_in = st.form_submit_button("🚀 Sign In", use_container_width=True)
        with col2:
            sign_up = st.form_submit_button("🔙 Back to Sign Up", use_container_width=True)

        if sign_in:
            login_user()
            
        if sign_up:
            navigate_to("logup")

def register_user() -> None:
    """Register a new user."""
    try:
        db_manager = get_db_manager()
        user_id = db_manager.register_user(
            first_name=st.session_state.first_name,
            last_name=st.session_state.last_name,
            email=st.session_state.reg_email,
            password=st.session_state.reg_password,
            phone=st.session_state.phone,
            birth_date=st.session_state.birth_date,
            address=st.session_state.address,
            city=st.session_state.city,
            country=st.session_state.country
        )
        st.success("Registration successful! Please login to continue.")
        navigate_to("login")
    except InvalidRegestrationDataError as e:
        st.error(str(e))
        for error in e.errors:
            st.error(error["error"])
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")

def render_register_view() -> None:
    """Render the registration view."""
    st.markdown(
        """
        <h2 style='text-align: center;'>🍲 Join mIAm 🍝</h2>
        <p style='text-align: center; color: gray;'>Create your account to get started.</p>
        """, 
        unsafe_allow_html=True
    )
    
    with st.form("register_form"):
        st.markdown("### 📝 Sign Up")

        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("👤 First Name *", key="first_name", placeholder="Enter your first name")
            st.text_input("📧 Email *", key="reg_email", placeholder="Enter your email")
            st.text_input("📱 Phone", key="phone", placeholder="Enter your phone number")
            st.text_input("🏠 Address", key="address", placeholder="Enter your address")
            st.text_input("🌍 Country", key="country", placeholder="Enter your country")
        
        with col2:
            st.text_input("👤 Last Name *", key="last_name", placeholder="Enter your last name")
            st.text_input("🔒 Password *", type="password", key="reg_password", placeholder="Create a strong password")
            st.date_input(
                "📅 Birth Date", key="birth_date",
                min_value=date(1900, 1, 1),
                max_value=date.today().replace(year=date.today().year - 18)
            )
            st.text_input("🏙️ City", key="city", placeholder="Enter your city")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            sign_up = st.form_submit_button("✅ Sign Up", use_container_width=True)
        with col2:
            sign_in = st.form_submit_button("🔙 Back to Sign In", use_container_width=True)
    
    if sign_up:
        register_user()
        
    if sign_in:
        navigate_to("login")

def logout() -> None:
    """Log out the user and reset session state."""
    session_keys = [
        "authenticated", "user_id", "user_profile", 
        "thread_id", "chat_history"
    ]
    
    for key in session_keys:
        st.session_state[key] = None if key != "authenticated" and key != "chat_history" else (False if key == "authenticated" else [])
    
    st.session_state.current_view = "login"
    
def create_new_thread() -> None:
    """Create a new chat thread."""
    try:
        db_manager = get_db_manager()
        thread_name = st.session_state.new_thread_name or f"Chat {uuid4().hex[:8]}"
        thread_id = db_manager.create_thread(
            user_id=st.session_state.user_id,
            thread_name=thread_name
        )
        select_thread(thread_id)
    except Exception as e:
        st.error(f"Error creating thread: {str(e)}")

def select_thread(thread_id: str) -> None:
    """Select an existing thread."""
    st.session_state.thread_id = thread_id
    st.session_state.chat_history = []  
    navigate_to("chat")

def format_thread_name(thread: Dict[str, Any]) -> str:
    """Format thread name and date for display."""
    thread_name = thread.get('thread_name', thread.get('name', f"Thread {thread['id']}"))
    created_at = thread.get('created_at')
    date_str = created_at.strftime('%Y-%m-%d') if created_at else "Unknown date"
    return f"**{thread_name}** (Created: {date_str})"

def render_sidebar() -> None:
    """Render the sidebar with conversation management options."""
    with st.sidebar:
        st.button("Logout", on_click=logout)
        with st.expander("💬 Create New Chat"):
            with st.form("new_chat_form"):
                st.text_input("Chat Name (optional)", key="new_thread_name")
                submit = st.form_submit_button("Create")
                if submit:
                    create_new_thread()
        
        st.markdown("### Your Conversations")
        db_manager = get_db_manager()
        threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
        
        if not threads:
            st.info("You don't have any conversations yet. Create a new one to get started!")
        else:
            for thread in threads:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(format_thread_name(thread))
                with col2:
                    st.button("Open", key=f"open_{thread['id']}", on_click=select_thread, args=(thread['id'],))

async def load_thread_history(thread_id: str) -> List[Dict[str, str]]:
    """Load chat history for a thread."""
    with st.spinner("Loading message history..."):
        return await load_chat_history(thread_id)

def stream_message(message: str) -> None:
    for word in message.split(" "):
        yield word + " "
        time.sleep(0.02)        
            
def render_chat() -> None:
    """Render the chat interface."""
    db_manager = get_db_manager()
    threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
    
    if threads:
        st.session_state.thread_id = st.session_state.thread_id or threads[0]["id"]
        current_thread = next((t for t in threads if t['id'] == st.session_state.thread_id), None)
        
        thread_name = current_thread.get('thread_name', current_thread.get('name', f"Thread {current_thread['id']}"))
    
        # Load chat history if not already loaded
        if not st.session_state.chat_history:
            st.session_state.chat_history = [
                {"role": "assistant", "content": CHAT_PROMPT},
            ] + asyncio.run(load_thread_history(st.session_state.thread_id))

        # Main chat area
        st.markdown(f"## Chat: {thread_name}")
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])        
        
        # User input area        
        if prompt := st.chat_input("Type your message here..."):
            if isinstance(prompt, str) and prompt.strip():
                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.chat_history.append({"role": "user", "content": prompt})

                # AI response
                with st.spinner("Thinking..."):
                    ai_response = asyncio.run(run_agent(prompt))
                    with st.chat_message("assistant"):
                        st.write_stream(stream_message(ai_response))  # Stream the response

                # Append AI response to chat history AFTER streaming it
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
    else:
        st.info("You don't have any conversations yet. Create a new one to get started!")


async def run_agent(user_message: str) -> str:
    """Run the agent with the user's message."""

    full_response = ""
    
    try:
        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }
        
        async with AsyncConnectionPool(
            conninfo=get_db_uri(),
            max_size=20,
            kwargs=connection_kwargs
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            
            # Set up the checkpointer
            await checkpointer.setup()
            
            graph = workflow.compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": str(st.session_state.thread_id)}}
            
            async for output in graph.astream(
                {"messages": [HumanMessage(content=user_message)]}, 
                config=config, 
                stream_mode="updates"
            ):
                if output:
                    try:
                        last_message = next(iter(output.values()))["messages"][-1]
                        if hasattr(last_message, "content"):
                            if isinstance(last_message.content, str):
                                full_response = last_message.content
                    except (StopIteration, IndexError, KeyError):
                        pass
            
    except Exception as e:
        error_message = f"Error processing your request: {str(e)}"
        full_response = error_message
    
    return full_response

def main() -> None:
    """Main application entry point."""
    init_session_state()
    
    if not st.session_state.authenticated:
        if st.session_state.current_view == "login":
            render_login_view()
        elif st.session_state.current_view == "logup":
            render_register_view()
    else: 
        if st.session_state.current_view == "chat":
            render_chat()
            render_sidebar()
            

if __name__ == "__main__":
    main()