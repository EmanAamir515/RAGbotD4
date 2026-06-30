import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
from agent import llm_response, get_session_history
from services import delete_session, register_session, get_user_sessions
from servicesFiles.upload_service import extract_text
from servicesFiles.STTvoice_services import STT_function
from auth.routes import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    from embeddings.embedding import _get_vector_store
    threading.Thread(target=_get_vector_store, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    register_session(user_email, session_id, title=message[:40])

    def event_stream():
        file_text = None
        if file_bytes:
            yield f"event: status\ndata: Reading {filename}\n\n"
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


@app.post('/tts')##not using for now trying line by line 
async def text_to_speech(data: dict):
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text provided to synthesize")
    try:
        from servicesFiles.TTS_services import audio as tts_audio
        audio_bytes = tts_audio(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")
    return Response(content=audio_bytes, media_type="audio/wav")