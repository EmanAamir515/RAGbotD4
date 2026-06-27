import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def render_chat_input(render_bubble):
    """
    Renders the chat input box (with + attach button for file upload),
    sends the message + optional file to /post_stream, and streams the
    response back into the chat.
    """
    prompt_data = st.chat_input(
        "Type your message !!!",
        accept_file=True,
        file_type=["pdf", "docx", "csv", "txt", "pptx"],
    )

    if not prompt_data:
        return

    prompt = prompt_data.text
    files = prompt_data.files

    display_text = prompt
    if files:
        display_text = f"📎 *{files[0].name}*\n\n{prompt}" if prompt else f"📎 *{files[0].name}*"

    st.session_state.messages.append({"role": "user", "content": display_text})
    st.markdown(render_bubble("user", display_text), unsafe_allow_html=True)

    message_placeholder = st.empty()
    status_placeholder = st.empty()
    full_response = ""

    form_data = {"Cid": st.session_state.conversation_id, "content": prompt}
    upload_files = {"file": (files[0].name, files[0].getvalue(), files[0].type)} if files else None

    status_placeholder.markdown("*Uploading...*" if files else "*Thinking...*")

    try:
        response = st.session_state.http.post(
            f"{BACKEND_URL}/post_stream",
            data=form_data,
            files=upload_files,
            stream=True,
            timeout=(10, 60),
        )

        if response.status_code != 200:
            status_placeholder.empty()
            st.error(f"Error: {response.status_code}")
            st.code(response.text)
            return

        current_event = "message"
        counter = 0
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
                    current_event = "message"
                    continue

                if data == "[DONE]":
                    break

                if not full_response:
                    status_placeholder.empty()
                full_response += data
                counter += 1
                if counter % 3 == 0:
                    message_placeholder.markdown(
                        render_bubble("assistant", full_response + "▌"), unsafe_allow_html=True
                    )

        status_placeholder.empty()
        message_placeholder.markdown(render_bubble("assistant", full_response), unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    except requests.exceptions.ConnectionError:
        status_placeholder.empty()
        st.error("Cannot connect to server. Make sure the backend (FastAPI) is running.")
    except requests.exceptions.Timeout:
        status_placeholder.empty()
        st.error("The server took too long to respond. Please try again.")
    except Exception as e:
        status_placeholder.empty()
        st.error(f"Unexpected error: {e}")