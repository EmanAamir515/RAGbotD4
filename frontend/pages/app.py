import uuid
import requests
import streamlit as st
import os
import base64

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="NetSol Chatbot", layout="wide")

# require login before showing the chat - send unauthenticated users back
# to the login page instead of letting them hit the chat with no identity
if not st.session_state.get("authenticated"):
    st.warning("Please log in to use the chat.")
    st.stop()

user_email = st.session_state.get("user_email", "guest_user")

st.title("🤖 NetSol Chatbot")

st.markdown("""
<style>
:root {
    --netsol-blue: #2563EB;
    --netsol-blue-dark: #1D4ED8;
    --netsol-blue-light: #EFF6FF;
    --netsol-text: #1E293B;
    --netsol-border: #E2E8F0;
}

/* Overall white background, dark readable text */
.stApp {
    background-color: #FFFFFF;
}
.stApp, .stApp p, .stApp span, .stApp label {
    color: var(--netsol-text);
}

/* Make room at the bottom of the message list so the last messages
   aren't hidden behind the fixed input bar. */
.block-container {
    padding-bottom: 7rem;
}

/* Sidebar: light blue tint to separate it from the white main area */
section[data-testid="stSidebar"] {
    background-color: var(--netsol-blue-light);
    border-right: 1px solid var(--netsol-border);
}

/* Chat bubbles: NetSol blue for the user's messages, soft white/gray for
   the assistant's - mirrors the logo's blue-on-white identity. */
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
    background-color: var(--netsol-blue);
    border-radius: 16px;
}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) p,
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) span {
    color: #FFFFFF;
}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
    background-color: #F8FAFC;
    border: 1px solid var(--netsol-border);
    border-radius: 16px;
}

/* Buttons: filled NetSol blue, rounded */
.stButton > button {
    background-color: var(--netsol-blue);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
}
.stButton > button:hover {
    background-color: var(--netsol-blue-dark);
    color: #FFFFFF;
}
.stButton > button[kind="secondary"] {
    background-color: #FFFFFF;
    color: var(--netsol-blue);
    border: 1px solid var(--netsol-blue);
}

/* The chat input is already fixed to the bottom of the viewport by
   Streamlit - this rounds it into a pill, gives it the NetSol border
   color, and reserves space on the right so the mic button can sit
   visually close to it. */
div[data-testid="stChatInput"] {
    border-radius: 28px;
    padding-right: 60px;
    border: 1px solid var(--netsol-border);
    background-color: #FFFFFF;
}

/* Audio input rendered as a small circular mic button in NetSol blue,
   absolutely positioned over the right side of the chat input pill
   (rather than in its own column, which would break the chat input's
   sticky-bottom behavior). Fixed to the viewport so it stays glued to
   the input bar regardless of how far the chat is scrolled. */
div[data-testid="stAudioInput"] {
    position: fixed;
    bottom: 40px;
    right: 90px;
    width: 44px;
    z-index: 1000;
    border-radius: 50%;
    overflow: hidden;
    border: 1px solid var(--netsol-blue);
}
div[data-testid="stAudioInput"] > div {
    border-radius: 50%;
    background-color: var(--netsol-blue-light);
}

/* Keep long error/warning text from overflowing its box - this is what
   was causing the cut-off "has occurred please..." message. */
div[data-testid="stAlert"] {
    overflow-wrap: break-word;
    word-break: break-word;
    white-space: normal;
}
</style>
""", unsafe_allow_html=True)

# --- Session ID: persist across refresh using the URL ---
query_params = st.query_params

if "session_id" in query_params:
    st.session_state.session_id = query_params["session_id"]
elif "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.query_params["session_id"] = st.session_state.session_id

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "loaded_session_id" not in st.session_state:
    st.session_state.loaded_session_id = None


def load_history(session_id):
    """Fetches this session's conversation from the backend (which reads
    it from the LangGraph checkpointer) and stores it for rendering. This
    is what makes switching chats - or reloading the page on an existing
    chat - actually restore the messages instead of showing a blank chat."""
    try:
        r = requests.get(f"{BACKEND_URL}/history/{session_id}", timeout=10)
        st.session_state.display_messages = r.json() if r.status_code == 200 else []
    except Exception:
        st.session_state.display_messages = []
    st.session_state.loaded_session_id = session_id


# Load history for the active session exactly once per session switch -
# not on every rerun, so newly-streamed messages in display_messages
# during this run aren't clobbered by a redundant re-fetch.
if st.session_state.loaded_session_id != st.session_state.session_id:
    load_history(st.session_state.session_id)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_sessions(user_email):
    try:
        r = requests.get(f"{BACKEND_URL}/sessions/{user_email}", timeout=5)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


# --- Sidebar: account info + multiple-chats list (like ChatGPT threads) ---
@st.dialog("Delete chat")
def confirm_delete_session(session_id, title):
    st.warning(f"Delete **{title}**? This permanently removes its messages and cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary", use_container_width=True):
            requests.delete(f"{BACKEND_URL}/session/{session_id}", timeout=10)
            fetch_sessions.clear()
            if st.session_state.session_id == session_id:
                # the active chat was just deleted - start a fresh one
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.display_messages = []
                st.session_state.loaded_session_id = st.session_state.session_id
                st.query_params["session_id"] = st.session_state.session_id
            st.rerun()


with st.sidebar:
    st.caption(f"Logged in as: {user_email}")

    if st.button("➕ New chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.display_messages = []
        st.session_state.loaded_session_id = st.session_state.session_id
        st.query_params["session_id"] = st.session_state.session_id
        st.rerun()

    st.divider()

    for s in fetch_sessions(user_email):
        is_active = s["session_id"] == st.session_state.session_id
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(
                s["title"],
                key=f"sess_{s['session_id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.session_id = s["session_id"]
                st.query_params["session_id"] = s["session_id"]
                st.rerun()  # history is (re)loaded at the top of the next run
        with col2:
            if st.button("🗑", key=f"del_{s['session_id']}"):
                confirm_delete_session(s["session_id"], s["title"])

    st.divider()
    if st.button("Log out", use_container_width=True):
        token = st.session_state.get("auth_token")
        if token:
            try:
                requests.post(f"{BACKEND_URL}/auth/logout", data={"token": token}, timeout=5)
            except Exception:
                pass
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.auth_token = None
        st.query_params.clear()
        st.switch_page("login_app.py")

# --- Render past messages ---
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Chat input: pinned to the bottom of the viewport (Streamlit's
# native behavior for st.chat_input, which only works when it's rendered
# directly rather than inside a column). The mic button is rendered right
# after it and pulled on top of the input pill via the CSS above, instead
# of living in a separate column that would break the sticky positioning. ---
prompt_data = st.chat_input(
    "Type your message",
    accept_file=True,
    file_type=["pdf", "docx", "csv", "txt", "pptx"],
)
audio_value = st.audio_input("🎤", label_visibility="collapsed", key="mic_input")

user_input = None
upload_file = None
is_voice_input = False

if prompt_data:
    user_input = prompt_data.text
    if prompt_data.files:
        upload_file = prompt_data.files[0]
elif audio_value:
    # guard against re-transcribing the same blob on unrelated reruns
    if audio_value.file_id != st.session_state.get("last_audio_id"):
        st.session_state.last_audio_id = audio_value.file_id
        with st.spinner("Transcribing..."):
            try:
                r = requests.post(
                    f"{BACKEND_URL}/stt",
                    files={"audio_file": ("recording.wav", audio_value.getvalue(), "audio/wav")},
                    timeout=30,
                )
                if r.status_code == 200:
                    user_input = r.json().get("text")
                    is_voice_input = True
                else:
                    st.error("Transcription failed")
            except Exception as e:
                st.error(f"Transcription error: {e}")

if user_input:
    # voice-transcribed messages are shown as plain text bubbles too - same
    # as typed messages, no waveform/audio player in the chat history
    display_text = f"📎 *{upload_file.name}*\n\n{user_input}" if upload_file else user_input
    st.session_state.display_messages.append({"role": "user", "content": display_text})
    with st.chat_message("user"):
        st.write(display_text)

    with st.chat_message("assistant"):
        form_data = {
            "message": user_input,
            "session_id": st.session_state.session_id,
            "user_email": user_email,
            "want_voice_reply": is_voice_input,
        }
        files = {"file": (upload_file.name, upload_file.getvalue(), upload_file.type)} if upload_file else None

        message_placeholder = st.empty()
        status_placeholder = st.empty()
        audio_placeholder = st.empty()
        full_reply = ""
        audio_queue = []  # sentence-by-sentence audio clips, played in order as they arrive

        try:
            response = requests.post(
                f"{BACKEND_URL}/chat",
                data=form_data,
                files=files,
                stream=True,
                timeout=(10, 90),
            )

            current_event = "message"
            for line in response.iter_lines(chunk_size=64):
                if not line:
                    continue
                line = line.decode("utf-8")

                if line.startswith("event: "):
                    current_event = line[7:]
                    continue

                if line.startswith("data: "):
                    data = line[6:]

                    if current_event == "status":
                        status_placeholder.markdown(f"*{data}*")
                        continue

                    if current_event == "audio":
                        # Play this sentence's audio now, alongside the text
                        # for later sentences still streaming in below -
                        # this is the "parallel" voice+text behavior.
                        audio_queue.append(base64.b64decode(data))
                        audio_placeholder.audio(audio_queue[-1], format="audio/wav", autoplay=True)
                        continue

                    if current_event == "done":
                        break

                    # current_event == "message"
                    if not full_reply:
                        status_placeholder.empty()  # clear the loader on first real token
                    full_reply += data
                    message_placeholder.markdown(full_reply + "▌")

            status_placeholder.empty()
            message_placeholder.markdown(full_reply)

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to server. Make sure the backend is running.")
        except requests.exceptions.Timeout:
            st.error("The server took too long to respond. Please try again.")

    st.session_state.display_messages.append({"role": "assistant", "content": full_reply})
    fetch_sessions.clear()  # refresh sidebar so a brand-new session shows up with its title