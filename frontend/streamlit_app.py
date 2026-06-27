import streamlit as st
import requests
import uuid
import markdown
import os
from chat_input import render_chat_input

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="eChatBot", page_icon="🤖", layout ="wide")
st.title("eChatBot")
## customized CSS styles 
st.markdown("""
<style>
.chat-row {
    display: flex;
    margin: 8px 0;
}
.chat-row.user {
    justify-content: flex-end;
}
.chat-row.assistant {
    justify-content: flex-start;
}
.bubble {
    padding: 10px 16px;
    border-radius: 16px;
    max-width: 85%;
    word-wrap: break-word;
}
.bubble.user {
    background-color: #e62e62;
    color: white;
    border-bottom-right-radius: 4px;
}
.bubble.assistant {
    background-color: #f1f1f1;
    color: #111;
    border-bottom-left-radius: 4px;
}
.bubble table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
    font-size: 0.9em;
}
.bubble th, .bubble td {
    border: 1px solid #ccc;
    padding: 6px 10px;
    text-align: left;
}
.bubble th {
    background-color: rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

def _fix_squeezed_markdown(content):
    """Safety net: if the model squeezes a markdown table or list onto a
    single line (no real newlines between rows), insert them so the
    Markdown table/list extensions can actually recognize the structure."""
    if "|" in content and content.count("\n") < content.count("|") / 4:
        # looks like a table crammed onto one line - break before each
        # row delimiter pattern "| <number or word> |" that starts a new row
        import re
        content = re.sub(r'\s*\|\s*(?=\d+\s*\|)', '\n| ', content)
        content = content.replace("||", "|\n|")
    return content


def render_bubble(role, content):
    content = _fix_squeezed_markdown(content)
    html = markdown.markdown(content , extensions=["tables", "fenced_code", "nl2br"])## converts **bold** into real html code and give output 
   # html = markdown.markdown(content)
    return f"""
    <div class="chat-row {role}">
        <div class="bubble {role}">{html}</div>
    </div>
    """
    
if "messages" not in st.session_state:##persists rerun fro given browser session
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
if "http" not in st.session_state:
    st.session_state.http = requests.Session()
    
    
@st.dialog("Confirm deletion")## deletion decorator
def confirm_delete(cid):
    st.warning(f"This will permanently delete all messages in conversation **{cid}**. This cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Yes, delete it", type="primary"):
            st.session_state.http.delete(f"{BACKEND_URL}/delete/{cid}")## calls delete API
            st.session_state.messages = []
            fetch_all_chats.clear()
            st.rerun()

@st.cache_data(ttl=60, show_spinner=False)  # refetch at most every 10s
def fetch_all_chats():
    try:
        response = st.session_state.http.get(f"{BACKEND_URL}/allChats", timeout=5)
        return response.json() if response.status_code == 200 else []
    except Exception:
        # backend unreachable, slow, or mid-restart - fail quietly so the
        # rest of the page (including the chat input box) still renders
        return []
    
# Sidebar
with st.sidebar:
    st.header("Conversations")
    if st.button(" New Chat", use_container_width=True):
        st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []
        fetch_all_chats.clear()

    all_cids = fetch_all_chats()

    for c in all_cids:
        col1, col2 = st.columns([4, 1])
        with col1:
            is_active = (c == st.session_state.conversation_id)
            if st.button(
                c,
                key=f"select_{c}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.conversation_id = c
                try:
                    h = st.session_state.http.get(f"{BACKEND_URL}/get/{c}", timeout=5)
                    st.session_state.messages = h.json() if h.status_code == 200 else []
                except Exception:
                    st.session_state.messages = []
                st.rerun()
            
        with col2:
            if st.button("🗑", key=f"delete_{c}"):
                confirm_delete(c)
        

for msg in st.session_state.messages:## prints msgs from oldest to newest
    if msg["role"] == "system":
        continue  # file-content notes aren't meant to be shown as chat bubbles
    st.markdown(render_bubble(msg["role"], msg["content"]), unsafe_allow_html=True)


# Chat input + file upload (logic lives in chat_input.py)
render_chat_input(render_bubble)