import os
import uuid
import base64
from langchain.agents import create_agent
from dotenv import load_dotenv
from embeddings.embedding import search_faq
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain_core.messages import AIMessageChunk
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/free"

SYSTEM_PROMPT = """You are NetSol's career assistant.
 
When you use search_faq, you will get back raw FAQ entries.
NEVER show raw retrieved text labelled with "Question:" or "Answer:" to the user.
NEVER copy-paste the retrieved text directly.
 
Instead:
 Read the retrieved information silently
 Synthesize a natural, conversational answer in your own words
 Combine info from multiple chunks into one coherent response if relevant
 Do not mention "Question:", "Answer:", or that you searched a knowledge base
 Just answer like a knowledgeable person would, directly addressing what the user asked
 
Example:
User: "how many clients does netsol have?"
Bad: "Question: How many clients... Answer: NetSol serves over 200 clients..."
Good: "NetSol serves over 200 clients globally, including Fortune 500 manufacturers, automakers, and government agencies — with more than 25,000 users across those organizations."
 
If a system message starts with "[Uploaded file content]", that text is the
full content of a document the user uploaded earlier in this conversation -
it is already given to you directly. When asked about that document,
read and use that content directly to answer, regardless of whether it's
related to NetSol or not. Do not say you cannot access the file.
 
Formatting rules for every response:
- Write in Markdown. Always put a blank line between paragraphs, between
  headings and the text that follows them, and between list items and
  the next paragraph - never run a heading or bold label directly into
  the sentence after it (e.g. never write "**Problem**Solar flares...";
  write "**Problem**\\n\\nSolar flares..." instead).
- For longer or multi-part answers (summaries, comparisons, step-by-step
  explanations), use short paragraphs and "- " bullet points instead of
  one dense block of text.
- For short, simple answers (a quick fact, a yes/no, one sentence), plain
  prose with no headings or bullets is fine - don't force structure where
  it isn't needed.
"""

_agent = None
langfuse_handler = None

def get_langfuse_handler():
    global langfuse_handler         
    if langfuse_handler is None and os.getenv("LANGFUSE_PUBLIC_KEY"):
        from langfuse.langchain import CallbackHandler
        langfuse_handler = CallbackHandler()
    return langfuse_handler


def _get_agent():
    global _agent
    if _agent is None:
        checkpointer = MongoDBSaver(
            client=client,
            db_name="chatbot_db",
            checkpoint_collection_name="checkpoints",
        )
        _agent = create_agent(
            ChatOpenRouter(model=MODEL, api_key=API_KEY, temperature=0),
            tools=[search_faq],
            checkpointer=checkpointer,
            system_prompt=SYSTEM_PROMPT,
        )
    return _agent


def get_or_create_session_id(session_id=None):
    return session_id or str(uuid.uuid4())


def get_session_history(session_id):
  
    agent = _get_agent()
    state = agent.get_state({"configurable": {"thread_id": session_id}})
    messages = state.values.get("messages", []) if state and state.values else []

    history = []
    for m in messages:
        role = getattr(m, "type", None)
        content = getattr(m, "content", "")
        if not content:
            continue
        if role == "human":
            history.append({"role": "user", "content": content})
        elif role == "ai":
            history.append({"role": "assistant", "content": content})
       
    return history


def _get_model_response(agent, messages, session_id, langfuse_handler, want_voice_reply):
  
    got_content = False
    config = {
        "configurable": {"thread_id": session_id},
        "callbacks": [h for h in [langfuse_handler] if h],
        "metadata": {"langfuse_session_id": session_id},
    }

    stream = agent.stream({"messages": messages}, config=config, stream_mode="messages")

    full_text = ""
    
    told_searching = False
    for chunk, metadata in stream:
        if not told_searching and metadata.get("langgraph_node") == "tools":
            yield "event: status\ndata: Searching NetSol FAQs...\n\n"
            told_searching = True
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            got_content = True
            safe_content = chunk.content.replace("\n", "\\n")
            yield f"event: message\ndata: {safe_content}\n\n"
            if want_voice_reply:
                full_text+=chunk.content
                
    if want_voice_reply and full_text.strip():
        yield from _emit_audio_event(full_text.strip())

    yield got_content  


def llm_response(message, session_id, file_text=None, want_voice_reply=False):
    messages = []
    if file_text:
     
        messages.append({
            "role": "system",
            "content": f"[Uploaded file content]\n\n{file_text}",
        })
    messages.append({"role": "user", "content": message})

    yield "event: status\ndata: Thinking...\n\n"

    agent = _get_agent()
    langfuse_handler = get_langfuse_handler()

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            got_content = False
            for item in _get_model_response(agent, messages, session_id, langfuse_handler, want_voice_reply):
                if isinstance(item, bool):
                    got_content = item  
                else:
                    yield item

            if got_content:
                break  

            print(f"Model '{MODEL}' returned an empty response (attempt {attempt}/{max_attempts})")

        except Exception as e:
            print(f"Model '{MODEL}' failed (attempt {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                yield "event: message\ndata: Sorry, I'm having trouble reaching the AI provider right now. Please try again in a moment.\n\n"

    yield "event: done\ndata: [DONE]\n\n"


def _emit_audio_event(sentence_text):
    try:
        from servicesFiles.TTS_services import audio as tts_audio
        audio_bytes = tts_audio(sentence_text)
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        yield f"event: audio\ndata: {b64}\n\n"
    except Exception as e:
        print(f"TTS failed for a sentence (continuing without audio for it): {e}")