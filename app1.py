import os
import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from tools import tool1_weather, tool2_stock_alpha, tool3_tavily_search

# --------------------------------------------------
# ENV
# --------------------------------------------------
load_dotenv()

# --------------------------------------------------
# LLM
# --------------------------------------------------
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile"
)

tools = [
    tool1_weather,
    tool2_stock_alpha,
    tool3_tavily_search
]

# --------------------------------------------------
# FAISS MEMORY
# --------------------------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = FAISS.from_texts(
        ["Conversation started"],
        embedding=embeddings
    )

def retrieve_memory(query, k=3):
    docs = st.session_state.vectorstore.similarity_search(query, k=k)
    return "\n".join(d.page_content for d in docs)

# --------------------------------------------------
# MEMORY YES / NO LOGIC
# --------------------------------------------------
def is_yes_no_memory_question(text: str) -> bool:
    triggers = [
        "did i ask",
        "did i mention",
        "have i asked",
        "before",
        "earlier",
        "previous"
    ]
    return any(t in text.lower() for t in triggers)

def memory_yes_no(query: str, threshold=0.6) -> str:
    results = st.session_state.vectorstore.similarity_search_with_score(
        query, k=3
    )
    for doc, score in results:
        if score < threshold:
            return "Yes"
    return "No"

# --------------------------------------------------
# PROMPT
# --------------------------------------------------
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant.\n"
        "Relevant past conversation:\n{context}\n"
        "Use tools ONLY if required."
    ),
    MessagesPlaceholder("messages"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False
)

# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------
st.set_page_config(page_title="Multi-Tool AI Chatbot", layout="centered")
st.title("🤖 Multi-Tool AI Chatbot with FAISS Memory")
st.markdown("Weather • Stocks • Web Search • Memory")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))

    # ---------------- MEMORY QUESTION ----------------
    if is_yes_no_memory_question(user_input):
        bot_reply = memory_yes_no(user_input)

    # ---------------- NORMAL QUESTION ----------------
    else:
        memory_context = retrieve_memory(user_input)

        with st.spinner("🤔 Thinking..."):
            try:
                response = agent_executor.invoke({
                    "messages": [HumanMessage(content=user_input)],
                    "context": memory_context
                })
                bot_reply = response["output"]
            except Exception as e:
                bot_reply = f"⚠️ Error: {str(e)}"

    # ---------------- SAVE TO MEMORY ----------------
    st.session_state.vectorstore.add_texts([
        f"User: {user_input}\nAssistant: {bot_reply}"
    ])

    st.session_state.chat_history.append(("bot", bot_reply))

# --------------------------------------------------
# RENDER CHAT
# --------------------------------------------------
for role, message in st.session_state.chat_history:
    if role == "user":
        st.chat_message("user").write(message)
    else:
        st.chat_message("assistant").markdown(message.replace("\n", "  \n"))
