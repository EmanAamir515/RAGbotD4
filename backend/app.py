from fastapi import FastAPI ##endpoint file like tmrw 
from models.free_model import ask_model_tooling
from data.structure import mem
from services.DBservices import store_msg, get_convoHistory,get_allconvos, delete_convo
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from services.embed import build_faq_embeddings, retrieve_relevant_faqs


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
async def add_msg_stream(data:mem):
    ## store user msg with role/id after it got reply 
    store_msg(data.Cid, 'user', data.content)
    
    history = get_convoHistory(data.Cid) ##history of chat for context 
    
    relevant_faqs = retrieve_relevant_faqs(data.content)
    if relevant_faqs:
   ## if found combines LLM + history chat (context) to answer
        context_text = "\n\n".join( f"Q: {f['question']}\nA: {f['answer']}" for f in relevant_faqs)
        system_msg = {
            "role": "system",
            "content": (
                "You are NetSol's support assistant. Use the following FAQ "
                "entries to answer the user's question if they are relevant. "
                "If the FAQs don't cover it, answer normally."
                "Do not use markdown tables."
                "Use bullet points instead."
                "write each bullet point in new line.\n\n"
                f"{context_text}"
            )
        }
        history = [system_msg] + history

    def event_generator():
        full_response = ""
        #print(full_response)

        for chunk in ask_model_tooling(history):## gets all chunks in SSE format
            full_response += chunk
            yield f"data: {chunk}\n\n"
        
        store_msg(data.Cid, 'assistant', full_response)##saving full response at end
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.delete("/delete/{cid}")
def delete(cid:str):
    return delete_convo(cid)

@app.get("/allChats")
async def list_allChats():
    return get_allconvos()




