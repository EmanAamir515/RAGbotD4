import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def render_chat_input(render_bubble):
    """
    Renders the chat input box (with + attach button for file upload)
    plus a mic input for voice messages. Sends the message (typed or
    transcribed) + optional file to /post_stream, streams the response
    back, and plays it back as speech via /tts.
    """
    prompt_data = st.chat_input(
        "Type your message !!!",
        accept_file=True,
        file_type=["pdf", "docx", "csv", "txt", "pptx"],
    )
    audio_value = st.audio_input("🎤", label_visibility="collapsed", key="mic_input")

    prompt = None
    files = None

    if prompt_data:
        prompt = prompt_data.text
        files = prompt_data.files
    elif audio_value:
        # guard against re-transcribing the same blob on unrelated reruns
        if audio_value.file_id != st.session_state.get("last_audio_id"):
            st.session_state.last_audio_id = audio_value.file_id
            audio_files = {"audio_file": ("recording.wav", audio_value.getvalue(), "audio/wav")}
            try:
                transcribe_response = st.session_state.http.post(
                    f"{BACKEND_URL}/STT", files=audio_files, timeout=30
                )
                if transcribe_response.status_code == 200:
                    prompt = transcribe_response.json()["text"]
                else:
                    st.error("Transcription failed")
            except Exception as e:
                st.error(f"Transcription error: {e}")

    if not prompt:
        return

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

        # speak the response back (best-effort - if TTS fails, the text
        # response above has already been shown, so just skip audio)
        try:
            tts_response = st.session_state.http.post(
                f"{BACKEND_URL}/tts", json={"text": full_response}, timeout=30
            )
            if tts_response.status_code == 200:
                st.audio(tts_response.content, format="audio/wav", autoplay=True)
        except Exception:
            pass

    except requests.exceptions.ConnectionError:
        status_placeholder.empty()
        st.error("Cannot connect to server. Make sure the backend (FastAPI) is running.")
    except requests.exceptions.Timeout:
        status_placeholder.empty()
        st.error("The server took too long to respond. Please try again.")
    except Exception as e:
        status_placeholder.empty()
        st.error(f"Unexpected error: {e}")