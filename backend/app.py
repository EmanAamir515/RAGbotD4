from services.gcs_sync import restore_from_gcs
restore_from_gcs()  # restores FAQ ChromaDB data; must run before embed.py creates its client

import threading
from fastapi import FastAPI, UploadFile, File, Form ##endpoint file like tmrw 
from models.free_model import ask_model_tooling
from services.DBservices import store_msg, get_convoHistory,get_allconvos, delete_convo
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from services.embed import build_faq_embeddings, retrieve_relevant_faqs
from services.upload_service import extract_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Builds FAQ embeddings in a background thread so the server starts
    # accepting requests immediately, instead of blocking startup for
    # however long the (free-tier, often slow) embedding API call takes.
    threading.Thread(target=build_faq_embeddings, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/get/{cid}")
async def get_hist(cid:str):
    return get_convoHistory(cid)

@app.post("/post_stream")
async def add_msg_stream(Cid: str = Form(...), content: str = Form(...), file: UploadFile = File(None)):
    file_bytes = await file.read() if file else None

    ## store user msg with role/id - prepend a small attachment badge if a file was sent
    stored_content = f"📎 *{file.filename}*\n\n{content}" if file else content
    store_msg(Cid, 'user', stored_content)

    history = get_convoHistory(Cid) ##history of chat for context 
    
#     relevant_faqs = retrieve_relevant_faqs(content)
#     if relevant_faqs:
#    ## if found combines LLM + history chat (context) to answer
#         context_text = "\n\n".join( f"Q: {f['question']}\nA: {f['answer']}" for f in relevant_faqs)
#         system_msg = {
#             "role": "system",
#             "content": (
#                 "You are NetSol's support assistant. Use the following FAQ "
#                 "entries to answer the user's question if they are relevant. "
#                 "If the FAQs don't cover it, answer normally."
#                 "Do not use markdown tables."
#                 "Use bullet points instead."
#                 "write each bullet point in new line.\n\n"
#                 f"{context_text}"
#             )
#         }
#         history = [system_msg] + history

    def event_generator():
        # If a file came with this message: extract its text and keep it
        # in-memory for this conversation (like Claude's own file handling -
        # no disk/vector DB persistence, just held in context up to a
        # character limit). Saved as a "system" message in MongoDB so it's
        # part of history for this and future turns in this conversation.
        nonlocal history
        if file_bytes:
            yield f"event: status\ndata: Reading {file.filename}...\n\n"

            file_text = extract_text(file.filename, file_bytes)
            if file_text:
                file_note = f"[Uploaded file: {file.filename}]\n\n{file_text}"
                store_msg(Cid, 'system', file_note)
                history = history + [{"role": "system", "content": file_note}]
                yield f"event: status\ndata: Added {file.filename} to conversation context\n\n"
            else:
                yield f"event: status\ndata: Could not extract text from {file.filename}\n\n"

        full_response = ""
        #print(full_response)

        for chunk in ask_model_tooling(history, Cid):## gets all chunks in SSE format
            full_response += chunk
            yield f"data: {chunk}\n\n"
        
        store_msg(Cid, 'assistant', full_response)##saving full response at end
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.delete("/delete/{cid}")
def delete(cid:str):
    return delete_convo(cid)

@app.get("/allChats")
async def list_allChats():
    return get_allconvos()