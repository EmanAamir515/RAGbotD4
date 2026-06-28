import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
from agent import llm_response, get_session_history
from services import delete_session, register_session, get_user_sessions
from upload_service import extract_text
from STTvoice_services import STT_function
from auth.routes import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-builds the FAQ vector store in a background thread so the
    # server starts accepting requests (and passes Cloud Run's startup
    # health check) immediately, instead of blocking on the embedding
    # API calls. The first /chat request that needs search_faq will
    # simply wait for _get_vector_store() if this hasn't finished yet.
    from embedding import _get_vector_store
    threading.Thread(target=_get_vector_store, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router, prefix="/auth")


@app.get('/history/{session_id}')
def history(session_id: str):
    return get_session_history(session_id)


@app.post('/chat')
async def chat(
    message: str = Form(...),
    session_id: str = Form(...),
    user_email: str = Form(...),
    want_voice_reply: bool = Form(False),
    file: UploadFile = File(None),
):
    file_bytes = await file.read() if file else None
    filename = file.filename if file else None

    # record this session under the user (first message becomes the title,
    # truncated) so the sidebar can list it - no-ops on later messages
    register_session(user_email, session_id, title=message[:40])

    def event_stream():
        file_text = None
        if file_bytes:
            yield f"event: status\ndata: Reading {filename}...\n\n"
            file_text = extract_text(filename, file_bytes)
            if file_text:
                yield f"event: status\ndata: Added {filename} to conversation context\n\n"
            else:
                yield f"event: status\ndata: Could not extract text from {filename}\n\n"

        yield from llm_response(message, session_id, file_text=file_text, want_voice_reply=want_voice_reply)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get('/sessions/{user_email}')
def list_sessions(user_email: str):
    return get_user_sessions(user_email)


@app.delete('/session/{session_id}')
def delete(session_id: str):
    return delete_session(session_id)


@app.post('/stt')
async def speech_to_text(audio_file: UploadFile = File(...)):
    audio_bytes = await audio_file.read()
    text = STT_function(audio_bytes)
    return {"text": text}


@app.post('/tts')
async def text_to_speech(data: dict):
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided to synthesize")
    try:
        from TTS_services import audio as tts_audio
        audio_bytes = tts_audio(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")
    return Response(content=audio_bytes, media_type="audio/wav")