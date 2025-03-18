import streamlit as st
import asyncio
from uuid import uuid4
from datetime import date
import os
import psycopg2
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import openai
from mIAm.app.utils import load_chat_history
from mIAm.postgres_db.exceptions import (
    InvalidAuthenticationDataError,
    InvalidRegestrationDataError,
    UserNotFoundError,
    InvalidPasswordError
)

# Load environment variables from .env file if it exists
load_dotenv()

# Check and set OpenAI API key
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets.get("OPENAI_API_KEY", "")

# After setting the API key, import the mIAm modules
from mIAm.graph.workflow import workflow
from mIAm.postgres_db.postgres_db_manager import PostgresDBManager

# Confiure page
st.set_page_config(
    page_title="mIAm",
    page_icon="🍲",
    # layout="centered",
    initial_sidebar_state="expanded",
)

# Database Configuration
@st.cache_resource
def get_db_manager():
    DB_URI = f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}" \
             f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}" \
             f"?sslmode={os.getenv('PSQL_SSLMODE')}"
    return PostgresDBManager(
        conn_string=DB_URI,
        initialize_db=True
    )
    
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

# Navigation functions
def navigate_to(view):
    st.session_state.current_view = view
    
# Login
def login_user():
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
        st.session_state.current_view = "chat_selection"
    except InvalidAuthenticationDataError as e:
        st.error(e)
        for error in e.errors:
            st.error(error["error"])
    except UserNotFoundError as e:
        st.error(e)
    except InvalidPasswordError as e:
        st.error(e)
    except Exception as e:
        st.error(f"Error logging in: {str(e)}")

# Function to render a more stylish login view
def render_login_view():
    st.markdown(
        """
        <h2 style='text-align: center;'>🍲 Welcome to mIAm 🍝</h2>
        <p style='text-align: center; color: gray;'>Please enter your credentials to continue.</p>
        """, 
        unsafe_allow_html=True
    )
    
    # Centered container for login form
    with st.form("login_form", clear_on_submit=False):
        st.markdown("### 🔑 Sign In")
        
        # Stylish input fields
        email = st.text_input("📧 Email *", key="email", placeholder="Enter your email", help="Your registered email")
        password = st.text_input("🔒 Password *", key="password", type="password", placeholder="Enter your password", help="Your secure password")
        
        # Submit buttons with layout
        col1, col2 = st.columns([1, 1])
        with col1:
            sign_in = st.form_submit_button("🚀 Sign In", use_container_width=True)
        with col2:
            sign_up = st.form_submit_button("🔙 Back to Sign Up", use_container_width=True)

        # Handle actions
        if sign_in:
            login_user()
            
        if sign_up:
            navigate_to("logup")

# Registration
def register_user():
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
        st.session_state.current_view = "login"
    except InvalidRegestrationDataError as e:
        st.error(e)
        for error in e.errors:
            st.error(error["error"])
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")


# Function to render a more stylish registration view
def render_register_view():
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
            first_name = st.text_input("👤 First Name *", key="first_name", placeholder="Enter your first name")
            reg_email = st.text_input("📧 Email *", key="reg_email", placeholder="Enter your email")
            phone = st.text_input("📱 Phone", key="phone", placeholder="Enter your phone number")
            address = st.text_input("🏠 Address", key="address", placeholder="Enter your address")
            country = st.text_input("🌍 Country", key="country", placeholder="Enter your country")
        
        with col2:
            last_name = st.text_input("👤 Last Name *", key="last_name", placeholder="Enter your last name")
            reg_password = st.text_input("🔒 Password *", type="password", key="reg_password", placeholder="Create a strong password")
            birth_date = st.date_input(
                "📅 Birth Date", key="birth_date",
                min_value=date(1900, 1, 1),
                max_value=date.today().replace(year=date.today().year - 18)
            )
            city = st.text_input("🏙️ City", key="city", placeholder="Enter your city")
        
        # Submit buttons with modern layout
        col1, col2 = st.columns([1, 1])
        with col1:
            sign_up = st.form_submit_button("✅ Sign Up", use_container_width=True)
        with col2:
            sign_in = st.form_submit_button("🔙 Back to Sin In", use_container_width=True)
    
    # Handle actions
    if sign_up:
        register_user()
        
    if sign_in:
        navigate_to("login")


def logout():
    # Reset session state
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_profile = None
    st.session_state.thread_id = None
    st.session_state.chat_history = []
    st.session_state.current_view = "login"
    
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
    st.session_state.chat_history = []  
    st.session_state.current_view = "chat"
         
def render_chat_selection_view():
    st.markdown(f"## Welcome, {st.session_state.user_profile['first_name']}!")
    
    with st.sidebar:
        st.button("Logout", on_click=logout)
        with st.expander("💬 Create New Chat"):
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
        
        
def main():
    init_session_state()
    
    if not st.session_state.authenticated:
        if st.session_state.current_view == "login":
            render_login_view()
        elif st.session_state.current_view == "logup":
            render_register_view()
    else: 
        if st.session_state.current_view == "chat_selection":
            render_chat_selection_view()
        elif st.session_state.current_view == "chat":
            render_chat_view()
    

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


if __name__ == "__main__":
    main()