from fastapi import FastAPI, UploadFile, File, Form ##endpoint file like tmrw 
from models.free_model import ask_model_tooling
from services.DBservices import store_msg, get_convoHistory,get_allconvos, delete_convo
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from services.embed import build_faq_embeddings, retrieve_relevant_faqs
from services.upload_service import store_upload, retrieve_relevant_uploads, extract_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the FastAPI server starts up # Loads cached FAQ embeddings from disk, or builds + caches them# the first time (see embed.py).
    build_faq_embeddings()
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
        # if a file came with this message: extract its text directly (no
        # extra embedding call needed for THIS turn - we already know it's
        # relevant since the user just attached it). Still store it in
        # ChromaDB in the background so future turns can retrieve it.
        nonlocal history
        if file_bytes:
            yield f"event: status\ndata: Reading {file.filename}...\n\n"

            file_text = extract_text(file.filename, file_bytes)
            if file_text:
                history = history + [{
                    "role": "system",
                    "content": f"The user just uploaded '{file.filename}'. Its content:\n\n{file_text[:6000]}"
                }]

            chunk_count = store_upload(Cid, file.filename, file_bytes)
            yield f"event: status\ndata: Added {chunk_count} chunks from {file.filename}\n\n"
        else:
            # no new file this turn - check if there's a relevant chunk from
            # a PREVIOUSLY uploaded file in this conversation. Only inject
            # it if it's genuinely close in meaning to this message.
            relevant_chunks = retrieve_relevant_uploads(Cid, content)
            if relevant_chunks:
                context_text = "\n\n---\n\n".join(relevant_chunks)
                history = history + [{
                    "role": "system",
                    "content": f"Relevant excerpts from the user's previously uploaded document(s):\n\n{context_text}"
                }]

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