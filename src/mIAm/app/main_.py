import streamlit as st
import asyncio
from uuid import uuid4
import os
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from mIAm.app.utils import load_chat_history
import openai

# Load environment variables from .env file if it exists
load_dotenv()

# Check and set OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets.get("OPENAI_API_KEY", "")

# After setting the API key, import the mIAm modules
from mIAm.graph.workflow import workflow
from mIAm.postgres_db.postgres_db_manager import PostgresDBManager

# Configure page
st.set_page_config(page_title="mIAm Agent", page_icon="🤖", layout="wide")

# Database Configuration
@st.cache_resource
def get_db_manager():
    DB_URI = f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}" \
             f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}" \
             f"?sslmode={os.getenv('PSQL_SSLMODE')}"
    
    return PostgresDBManager(conn_string=DB_URI, initialize_db=True)

# Initialize session state variables
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_view" not in st.session_state:
        st.session_state.current_view = "login"
    if "api_key_set" not in st.session_state:
        st.session_state.api_key_set = "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"] != ""

# Reset authentication state
def logout():
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_profile = None
    st.session_state.thread_id = None
    st.session_state.chat_history = []
    st.session_state.current_view = "login"

# Set OpenAI API key
def set_api_key():
    if st.session_state.openai_api_key:
        os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
        st.session_state.api_key_set = True
        st.success("API Key set successfully!")
        st.experimental_rerun()

# Navigation functions
def navigate_to(view):
    st.session_state.current_view = view


def login_user():
    try:
        db_manager = get_db_manager()
        user = db_manager.authenticate_user(
            email=st.session_state.email,
            password=st.session_state.password
        )
        
        if user:
            st.session_state.authenticated = True
            st.session_state.user_id = user["id"]
            st.session_state.user_profile = db_manager.get_user_profile(user_id=user["id"])
            st.session_state.chat_history = []  # Reset chat history on login
            st.session_state.current_view = "chat_selection"
        else:
            st.error("Invalid credentials")
    except Exception as e:
        st.error(f"Login error: {str(e)}")

def register_user():
    try:
        db_manager = get_db_manager()
        user = db_manager.register_user(
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
        st.success("Registration successful! Please log in.")
        st.session_state.current_view = "login"
    except Exception as e:
        st.error(f"Registration error: {str(e)}")

def create_new_thread():
    try:
        db_manager = get_db_manager()
        thread_name = st.session_state.new_thread_name or f"Chat {uuid4().hex[:8]}"
        thread_id = db_manager.create_thread(
            user_id=st.session_state.user_id,
            thread_name=thread_name
        )
        st.session_state.thread_id = thread_id
        st.session_state.chat_history = []
        st.session_state.current_view = "chat"
    except Exception as e:
        st.error(f"Error creating thread: {str(e)}")

def select_thread(thread_id):
    st.session_state.thread_id = thread_id
    st.session_state.chat_history = []  # Reset chat history when switching threads
    st.session_state.current_view = "chat"

# Async function to run the agent
async def run_agent(user_message):
    DB_URI = f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}" \
             f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}" \
             f"?sslmode={os.getenv('PSQL_SSLMODE')}"
    
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_message})
    
    # Placeholder for AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            async with AsyncConnectionPool(
                conninfo=DB_URI,
                max_size=20,
                kwargs=connection_kwargs
            ) as pool:
                checkpointer = AsyncPostgresSaver(pool)
                
                # Check if we need to set up the checkpointer
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
                                    message_placeholder.markdown(full_response + "▌")
                        except (StopIteration, IndexError, KeyError):
                            pass
                
                # Final update without the cursor
                message_placeholder.markdown(full_response)
        except Exception as e:
            error_message = f"Error processing your request: {str(e)}"
            message_placeholder.markdown(f"⚠️ {error_message}")
            full_response = error_message
    
    # Add AI response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
    
    return full_response

# Function to render API key setup view
def render_api_key_setup():
    st.markdown("## 🔑 OpenAI API Key Setup")
    st.warning("An OpenAI API key is required to use the mIAm agent.")
    
    with st.form("api_key_form"):
        st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        submit = st.form_submit_button("Set API Key")
    
    if submit:
        set_api_key()
    
    st.markdown("""
    ### How to get an OpenAI API key:
    1. Go to [platform.openai.com](https://platform.openai.com/)
    2. Sign up or log in to your account
    3. Navigate to API keys section
    4. Create a new API key
    5. Copy the key and paste it above
    
    Note: Your API key is only stored in your session and is not saved by this application.
    """)

# Function to render login view
def render_login_view():
    st.markdown("## 🤖 mIAm Login")
    
    with st.form("login_form"):
        st.text_input("Email", key="email")
        st.text_input("Password", type="password", key="password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Login")
        with col2:
            register_button = st.form_submit_button("Register Instead")
    
    if submit:
        login_user()
    
    if register_button:
        navigate_to("register")

# Function to render registration view
def render_register_view():
    st.markdown("## 🤖 mIAm Registration")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("First Name", key="first_name")
            st.text_input("Email", key="reg_email")
            st.text_input("Phone", key="phone")
            st.text_input("Address", key="address")
            st.text_input("Country", key="country")
        
        with col2:
            st.text_input("Last Name", key="last_name")
            st.text_input("Password", type="password", key="reg_password")
            st.date_input("Birth Date", key="birth_date")
            st.text_input("City", key="city")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Register")
        with col2:
            back_button = st.form_submit_button("Back to Login")
    
    if submit:
        register_user()
    
    if back_button:
        navigate_to("login")

# Function to render thread selection view
def render_chat_selection_view():
    st.markdown(f"## Welcome, {st.session_state.user_profile['first_name']}!")
    
    with st.sidebar:
        st.header("Profile")
        st.write(f"Name: {st.session_state.user_profile['first_name']} {st.session_state.user_profile['last_name']}")
        st.write(f"Email: {st.session_state.user_profile['email']}")
        st.button("Logout", on_click=logout)
    
    # Create new chat
    with st.expander("Create New Chat"):
        with st.form("new_chat_form"):
            st.text_input("Chat Name (optional)", key="new_thread_name")
            submit = st.form_submit_button("Create")
            if submit:
                create_new_thread()
    
    # List existing chats
    st.markdown("### Your Conversations")
    
    db_manager = get_db_manager()
    threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
    
    if not threads:
        st.info("You don't have any conversations yet. Create a new one to get started!")
    else:
        for thread in threads:
            col1, col2 = st.columns([3, 1])
            with col1:
                # Check for the keys that exist in the thread object
                thread_name = thread.get('thread_name', thread.get('name', f"Thread {thread['id']}"))
                created_at = thread.get('created_at', None)
                date_str = created_at.strftime('%Y-%m-%d') if created_at else "Unknown date"
                
                st.write(f"**{thread_name}** (Created: {date_str})")
            with col2:
                st.button("Open", key=f"open_{thread['id']}", on_click=select_thread, args=(thread['id'],))

        
# Fonction modifiée pour le rendu de la vue de chat
def render_chat_view():
    db_manager = get_db_manager()
    threads = db_manager.get_user_threads(user_id=st.session_state.user_id)
    current_thread = next((t for t in threads if t['id'] == st.session_state.thread_id), None)
    
    if not current_thread:
        st.error("Thread not found")
        navigate_to("chat_selection")
        return
    
    # Charger l'historique des messages si ce n'est pas déjà fait
    if not st.session_state.chat_history:
        with st.spinner("Chargement de l'historique des messages..."):
            st.session_state.chat_history = asyncio.run(load_chat_history(st.session_state.thread_id))
    
    # Sidebar with thread selection
    with st.sidebar:
        st.header("Navigation")
        st.button("← Back to Chats", on_click=navigate_to, args=("chat_selection",))
        st.button("Logout", on_click=logout)
        
        st.header("Current Chat")
        thread_name = current_thread.get('thread_name', current_thread.get('name', f"Thread {current_thread['id']}"))
        created_at = current_thread.get('created_at', None)
        date_str = created_at.strftime('%Y-%m-%d') if created_at else "Unknown date"
        
        st.write(f"**{thread_name}**")
        st.write(f"Created: {date_str}")
    
    # Main chat area
    st.markdown(f"## Chat: {thread_name}")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        asyncio.run(run_agent(prompt))

# Main app logic
def main():
    init_session_state()
    
    # Check if OpenAI API key is set
    if not st.session_state.api_key_set:
        render_api_key_setup()
        return
    
    # Render the appropriate view based on session state
    if not st.session_state.authenticated:
        if st.session_state.current_view == "login":
            render_login_view()
        elif st.session_state.current_view == "register":
            render_register_view()
    else:
        if st.session_state.current_view == "chat_selection":
            render_chat_selection_view()
        elif st.session_state.current_view == "chat":
            render_chat_view()

if __name__ == "__main__":
    main()