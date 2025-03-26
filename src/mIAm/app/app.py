import streamlit as st
import asyncio
from uuid import uuid4
from datetime import date
import os
from typing import Dict, List, Any, Optional, Tuple
import logging
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import time
from mIAm import setup_logger
from pathlib import Path
from email_validator import validate_email, EmailNotValidError

# Define the ROOT directory
ROOT = Path(__file__).resolve().parents[3]

# Configure logging
logger = setup_logger(console_logging_enabled=False, log_level=logging.INFO)

# Load environment variables first
load_dotenv()

# Initialize OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets.get("OPENAI_API_KEY", "")

# Import mIAm modules after setting API key
from mIAm.graph.workflow import workflow
from mIAm.graph.prompts import CHAT_PROMPT
from mIAm.app.utils import load_chat_history
from mIAm.postgres_db.postgres_db_manager import PostgresDBManager
from mIAm.postgres_db.exceptions import (
    InvalidAuthenticationDataError,
    InvalidRegestrationDataError,
    UserNotFoundError,
    InvalidPasswordError
)

# Page configuration
st.set_page_config(
    page_title="mIAm - Your AI Cooking Assistant",
    page_icon="🍲",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/mIAm',
        'Report a bug': 'https://github.com/yourusername/mIAm/issues',
        'About': "# mIAm 🍲\nYour AI-powered cooking assistant."
    }
)

# Application constants
APP_NAME = "mIAm"
APP_ICON = "🍲"
RESPONSE_STREAM_DELAY = 0.02  # seconds between words in the response stream

# ===== Database Configuration =====
def get_db_uri() -> str:
    """Generate Supabase connection URI from environment variables."""
    try:
        return (
            f"postgresql://postgres.fagpasxtuxuwhbkkeowy:{os.getenv('SUPABASE_DB_PASSWORD')}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
        )
    except Exception as e:
        logger.error(f"Failed to get database URI: {e}")
        st.error(f"Database connection error: {str(e)}")
        raise EnvironmentError("Database connection error")

@st.cache_resource
def get_db_manager() -> PostgresDBManager:
    """Get database manager instance (cached)."""
    try:
        return PostgresDBManager(
            conn_string=get_db_uri(),
            initialize_db=True
        )
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")
        st.error(f"Database connection error: {str(e)}")
        raise

@asynccontextmanager
async def get_db_pool():
    """Create and manage a database connection pool."""
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    
    pool = AsyncConnectionPool(
        conninfo=get_db_uri(),
        max_size=20,
        kwargs=connection_kwargs
    )
    
    try:
        await pool.open()
        yield pool
    finally:
        await pool.close()

# ===== Session Management =====
def init_session_state() -> None:
    """Initialize session state variables."""
    defaults = {
        "authenticated": False,
        "user_id": None,
        "user_profile": None,
        "thread_id": None,
        "chat_history": [],
        "current_view": "login",
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY", "")),
        "loading_history": False,
        "error": None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def navigate_to(view: str) -> None:
    """Navigate to a specific view."""
    st.session_state.current_view = view
    st.session_state.error = None  # Clear any errors when navigating

def logout() -> None:
    """Log out the user and reset session state."""
    for key in ["authenticated", "user_id", "user_profile", "thread_id", "chat_history"]:
        st.session_state[key] = None if key not in ["authenticated", "chat_history"] else (False if key == "authenticated" else [])
    
    st.session_state.current_view = "login"
    st.rerun()

# ===== Authentication Functions =====
def login_user() -> None:
    """Authenticate user and set session state."""
    try:
        email = st.session_state.get("email", "").strip()
        password = st.session_state.get("password", "")
        
        if not email or not password:
            st.error("Email and password are required.")
            return
            
        db_manager = get_db_manager()
        user = db_manager.authenticate_user(email=email, password=password)
        
        st.session_state.authenticated = True
        st.session_state.user_id = user["id"]
        st.session_state.user_profile = db_manager.get_user_profile(user_id=user["id"])
        st.session_state.chat_history = []
        
        st.success("Login successful!")
        navigate_to("chat")
        st.rerun()
    except (InvalidAuthenticationDataError, UserNotFoundError, InvalidPasswordError) as e:
        st.error(str(e))
        if hasattr(e, 'errors') and e.errors:
            for error in e.errors:
                st.error(error["error"])
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        st.error(f"An unexpected error occurred during login. Please try again.")

def register_user() -> None:
    """Register a new user."""
    try:
        # Validate required fields
        required_fields = ["first_name", "last_name", "reg_email", "reg_password"]
        for field in required_fields:
            if not st.session_state.get(field, "").strip():
                st.error(f"{field.replace('_', ' ').title()} is required.")
                return
        
        # Basic email validation
        email = st.session_state.get("reg_email", "").strip()
        try:
            # Validate and normalize the email address
            valid_email = validate_email(email)
            # Update with the normalized form
            normalized_email = valid_email.normalized
        except EmailNotValidError as e:
            # Affiche l'erreur directement dans l'interface Streamlit
            st.error(f"Invalid Email: {str(e)}")
            return
            
        # Password strength check
        password = st.session_state.get("reg_password", "")
        if len(password) < 8:
            st.error("Password must be at least 8 characters long.")
            return
            
        db_manager = get_db_manager()
        user_id = db_manager.register_user(
            first_name=st.session_state.first_name,
            last_name=st.session_state.last_name,
            email=normalized_email.lower(),
            password=st.session_state.reg_password,
            phone=st.session_state.get("phone", ""),
            birth_date=st.session_state.get("birth_date", date.today()),
            address=st.session_state.get("address", ""),
            city=st.session_state.get("city", ""),
            country=st.session_state.get("country", "")
        )
        
        st.success("Registration successful! Please login to continue.")
        navigate_to("login")
        st.rerun()
    except InvalidRegestrationDataError as e:
        st.error(str(e))
        if hasattr(e, 'errors') and e.errors:
            for error in e.errors:
                st.error(error["error"])
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        st.error(f"An unexpected error occurred during registration. Please try again.")

# ===== Thread Management =====
def create_new_thread() -> None:
    """Create a new chat thread."""
    try:
        db_manager = get_db_manager()
        thread_name = st.session_state.get("new_thread_name", "").strip() or f"Chat {uuid4().hex[:8]}"
        thread_id = db_manager.create_thread(
            user_id=st.session_state.user_id,
            thread_name=thread_name
        )
        select_thread(thread_id)
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        st.error(f"Failed to create a new chat thread. Please try again.")

def select_thread(thread_id: str) -> None:
    """Select an existing thread."""
    st.session_state.thread_id = thread_id
    st.session_state.chat_history = []
    navigate_to("chat")
    st.rerun()

def format_thread_name(thread: Dict[str, Any]) -> str:
    """Format thread name and date for display."""
    thread_name = thread.get('thread_name', thread.get('name', f"Thread {thread['id']}"))
    created_at = thread.get('created_at')
    date_str = created_at.strftime('%Y-%m-%d') if created_at else "Unknown date"
    return f"**{thread_name}** (Created: {date_str})"

def delete_thread(thread_id: str) -> None:
    """Delete a thread."""
    if st.session_state.thread_id == thread_id:
        st.session_state.thread_id = None
        st.session_state.chat_history = []
    
    try:
        db_manager = get_db_manager()
        db_manager.delete_thread(thread_id)
        logger.info(f"Thread {thread_id} deleted successfully.")
        # st.success("Thread deleted successfully.")
        st.rerun()
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        st.error(f"Failed to delete the thread. Please try again.")

# ===== Chat Logic =====
async def load_thread_history(thread_id: str) -> List[Dict[str, str]]:
    """Load chat history for a thread."""
    try:
        return await load_chat_history(thread_id)
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}")
        st.error("Failed to load chat history. Please try refreshing the page.")
        return []


def stream_message(message: str) -> str:
    """Generator for streaming words in a message."""
    for word in message.split(" "):
        yield word + " "
        time.sleep(RESPONSE_STREAM_DELAY)

async def run_agent(user_message: str) -> str:
    """Run the agent with the user's message."""
    full_response = ""
    
    try:
        async with get_db_pool() as pool:
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
                        if hasattr(last_message, "content") and isinstance(last_message.content, str):
                            full_response = last_message.content
                    except (StopIteration, IndexError, KeyError):
                        pass
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        full_response = f"I'm sorry, I encountered an error processing your request. Please try again in a moment."
    
    return full_response

# ===== UI Components =====
def render_header() -> None:
    """Render the application header."""
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<h1 style='text-align: center;'>{APP_ICON}</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<h1 style='margin-top: 0px;'>{APP_NAME}</h1>", unsafe_allow_html=True)
    st.divider()

def render_login_view() -> None:
    """Render the login view."""
    render_header()
    
    st.markdown(
        """
        <p style='text-align: center; color: gray;'>Please enter your credentials to continue.</p>
        """, 
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(str(ROOT / "images/login.jpg"), use_container_width=True)
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔑 Sign In")
            
            st.text_input("📧 Email *", key="email", placeholder="Enter your email", help="Your registered email")
            st.text_input("🔒 Password *", key="password", type="password", placeholder="Enter your password", help="Your secure password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                sign_in = st.form_submit_button("🚀 Sign In", use_container_width=True)
            with col2:
                sign_up = st.form_submit_button("📝 Sign Up", use_container_width=True)

            if sign_in:
                login_user()
                
            if sign_up:
                navigate_to("logup")
                st.rerun()

def render_register_view() -> None:
    """Render the registration view."""
    render_header()
    
    st.markdown(
        """
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
                max_value=date.today().replace(year=date.today().year - 18),
                help="You must be at least 18 years old to register"
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
        st.rerun()

def render_sidebar() -> None:
    """Render the sidebar with conversation management options."""
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.user_profile.get('first_name', 'User')}!")
        st.button("📤 Logout", on_click=logout, use_container_width=True)
        
        st.divider()
        
        with st.expander("💬 Create New Chat", expanded=True):
            with st.form("new_chat_form", clear_on_submit=True):
                st.text_input("Chat Name (optional)", key="new_thread_name")
                submit = st.form_submit_button("🆕 Create New Chat", use_container_width=True)
                if submit:
                    create_new_thread()
        
        st.markdown("### Your Conversations")
        db_manager = get_db_manager()
        threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
        
        if not threads:
            st.info("You don't have any conversations yet. Create a new one to get started!")
        else:
            for thread in threads:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(format_thread_name(thread))
                    with col2:
                        st.button("🔍", key=f"open_{thread['id']}", on_click=select_thread, args=(thread['id'],), help="Open this chat")
                    with col3:
                        st.button("🗑️", key=f"delete_{thread['id']}", on_click=delete_thread, args=(thread['id'],), help="Delete this chat")
                st.divider()

def render_chat() -> None:
    """Render the chat interface."""
    db_manager = get_db_manager()
    threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
    
    if not threads:
        st.info("You don't have any conversations yet. Create a new one to get started!")
        return
    
    # Select first thread if none is selected
    if not st.session_state.thread_id:
        st.session_state.thread_id = threads[0]["id"]
    
    current_thread = next((t for t in threads if t['id'] == st.session_state.thread_id), None)
    if not current_thread:
        st.warning("The selected thread no longer exists. Please select another thread.")
        st.session_state.thread_id = None
        st.session_state.chat_history = []
        return
    
    thread_name = current_thread.get('thread_name', current_thread.get('name', f"Thread {current_thread['id']}"))
    
    # Load chat history if not already loaded
    if not st.session_state.chat_history:
        with st.spinner("Loading conversation history..."):
            st.session_state.loading_history = True
            st.session_state.chat_history = [
                {"role": "assistant", "content": CHAT_PROMPT},
            ] + asyncio.run(load_thread_history(st.session_state.thread_id))
            st.session_state.loading_history = False

    # Main chat area
    st.markdown(f"## 💬 {thread_name}")
    
    # Chat container with scrolling
    chat_container = st.container()
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])        
    
    # User input area
    if not st.session_state.loading_history:
        prompt = st.chat_input("Type your message here...")
        if isinstance(prompt, str) and prompt.strip():
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            # AI response
            with st.spinner("Thinking..."):
                try:
                    ai_response = asyncio.run(run_agent(prompt))
                    with st.chat_message("assistant"):
                        st.write_stream(stream_message(ai_response))

                    # Append AI response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    logger.error(f"Error generating response: {str(e)}")
                    with st.chat_message("assistant"):
                        st.error("I'm sorry, I encountered an error while processing your message. Please try again.")
                    st.session_state.chat_history.append({"role": "assistant", "content": "I'm sorry, I encountered an error while processing your message."})

def render_error_page() -> None:
    """Render an error page."""
    st.error("An unexpected error occurred. Please refresh the page and try again.")
    if st.session_state.error:
        st.error(st.session_state.error)
    
    if st.button("Return to Login"):
        st.session_state.current_view = "login"
        st.session_state.error = None
        st.rerun()

# ===== Main Application =====
def main() -> None:
    """Main application entry point."""
    try:
        init_session_state()
        
        if not st.session_state.api_key_set:
            st.error("OpenAI API key is not set. Please check your environment variables or secrets.")
            return
        
        if st.session_state.current_view == "error":
            render_error_page()
        elif not st.session_state.authenticated:
            if st.session_state.current_view == "login":
                render_login_view()
            elif st.session_state.current_view == "logup":
                render_register_view()
            else:
                navigate_to("login")
                st.rerun()
        else: 
            if st.session_state.current_view == "chat":
                render_chat()
                render_sidebar()
            else:
                navigate_to("chat")
                st.rerun()
    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}")
        st.session_state.error = str(e)
        st.session_state.current_view = "error"
        st.rerun()

if __name__ == "__main__":
    main()