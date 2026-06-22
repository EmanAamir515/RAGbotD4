import streamlit as st
import requests
import uuid
import markdown

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

def render_bubble(role, content):
   ## html = markdown.markdown(content , extensions=["tables", "fenced_code", "nl2br"])## converts **bold** into real html code and give output 
    html = markdown.markdown(content)
    return f"""
    <div class="chat-row {role}">
        <div class="bubble {role}">{html}</div>
    </div>
    """
    
if "messages" not in st.session_state:##persists rerun fro given browser session
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = "conv_001"
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
            st.session_state.http.delete(f"http://localhost:8000/delete/{cid}")## calls delete API
            st.session_state.messages = []
            fetch_all_chats.clear()
            st.rerun()

@st.cache_data(ttl=40)  # refetch at most every 10s
def fetch_all_chats():
    try:
        response = st.session_state.http.get("http://localhost:8000/allChats")
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.ConnectionError:
        return []
    
# Sidebar
with st.sidebar:
    ##st.header("sideBar")
    
    st.header("Conversations")
    if st.button(" New Chat", use_container_width=True):
        st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        display_name = st.session_state.messages[0]["content"][:20]+ "..." if st.session_state.messages else st.session_state.conversation_id
        
        st.session_state.messages = []
        fetch_all_chats.clear()
        ##st.rerun()

  ##  st.divider() ##horizontal line 
    all_cids = fetch_all_chats()
    
    # all_cids = []
    
    # try:
    #     response = requests.get(f"http://localhost:8000/allChats")
    #     all_cids = response.json() if response.status_code == 200 else []
    # except requests.exceptions.ConnectionError:
    #     st.error("Cannot reach server")
    
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
                    h = st.session_state.http.get(f"http://localhost:8000/get/{c}")
                    st.session_state.messages = h.json() if h.status_code == 200 else []
                except requests.exceptions.ConnectionError:
                    st.session_state.messages = []
                st.rerun()
            
        with col2:
            if st.button("🗑", key=f"delete_{c}"):
                confirm_delete(c)
        

for msg in st.session_state.messages:## prints msgs from oldest to newest
    st.markdown(render_bubble(msg["role"], msg["content"]), unsafe_allow_html=True)


# Chat input
if prompt := st.chat_input("Type your message !!!"):

    st.session_state.messages.append({"role": "user", "content": prompt})## add new msg in state 
    st.markdown(render_bubble("user", prompt), unsafe_allow_html=True)

    message_placeholder = st.empty()
    
    full_response = ""
        
    try:
            # Use streaming endpoint
            response = st.session_state.http.post(
                "http://localhost:8000/post_stream",
                json={
                    "Cid": st.session_state.conversation_id,
                    "role": "user",
                    "content": prompt
                },
                stream=True ##lets us read as server sends it 
            )
            
            if response.status_code == 200:
                counter = 0
                for line in response.iter_lines(chunk_size=1):##send chunks of data SSE format
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            full_response += data
                            counter += 1
                            
                            if counter % 3 ==0:
                                message_placeholder.markdown(render_bubble("assistant", full_response + "▌"), unsafe_allow_html=True)                
                message_placeholder.markdown(render_bubble("assistant",full_response),unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                st.error(f"Error: {response.status_code}")
                
    except requests.exceptions.ConnectionError:
        st.error(" Cannot connect to server. Make sure FastAPI is running!")
    except Exception as e:
        st.error(f" Error: {str(e)}")

