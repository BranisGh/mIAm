import streamlit as st
import os
import asyncio
import time
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage

from mIAm.graph.workflow import workflow
from mIAm.graph.trimmer import TRIMMER

# Configuration de la page Streamlit
st.set_page_config(page_title="mIAm Chat", page_icon="💬", layout="wide")
st.title("mIAm Chat Assistant")

# Configuration de la base de données
@st.cache_resource
def get_db_uri():
    return (f"postgresql://{os.getenv('PSQL_USERNAME')}:{os.getenv('PSQL_PASSWORD')}"
            f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{os.getenv('PSQL_DATABASE')}"
            f"?sslmode={os.getenv('PSQL_SSLMODE')}")

DB_URI = get_db_uri()
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# Initialisation de l'état de session si inexistant
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "1"  # Par défaut ou générer un ID unique

# Affichage des messages existants
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Fonction asynchrone pour gérer la génération de réponses
async def generate_response(prompt):
    async with AsyncConnectionPool(
        conninfo=DB_URI,
        max_size=20,
        kwargs=connection_kwargs
    ) as pool:
        # Initialiser le checkpointer
        checkpointer = AsyncPostgresSaver(pool)
        try:
            await checkpointer.setup()
        except:
            # La table existe déjà probablement
            pass

        # Compiler le graphe avec le checkpointer
        graph = workflow.compile(checkpointer=checkpointer)
        
        # Configurer avec le thread_id de la session
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        # Préparation du placeholder pour la réponse de l'IA
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Streaming de la réponse avec mode "values" pour un streaming plus granulaire
            async for output in graph.astream(
                {"messages": [HumanMessage(content=prompt)]}, 
                config=config, 
                stream_mode="values"
            ):
                if output and "messages" in output:
                    messages = output["messages"]
                    if messages and len(messages) > 0:
                        last_message = messages[-1]
                        if isinstance(last_message, AIMessage) and last_message.content:
                            # Récupérer uniquement le nouveau contenu depuis la dernière mise à jour
                            new_content = last_message.content
                            if len(new_content) > len(full_response):
                                # Afficher progressivement le nouveau contenu
                                full_response = new_content
                                message_placeholder.markdown(full_response + "▌")
                                # Petit délai pour rendre l'affichage plus naturel
                                await asyncio.sleep(0.01)
            
            # Affichage de la réponse finale sans le curseur
            message_placeholder.markdown(full_response)
            
        # Ajouter la réponse à l'historique
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Saisie utilisateur
if prompt := st.chat_input("Comment puis-je vous aider aujourd'hui?"):
    # Ajouter le message utilisateur à l'historique
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Afficher le message utilisateur
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Générer la réponse
    asyncio.run(generate_response(prompt))

# Bouton pour effacer la conversation
if st.button("Nouvelle conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = str(int(st.session_state.thread_id) + 1)
    st.rerun()