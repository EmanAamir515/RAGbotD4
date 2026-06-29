import os
import re
import uuid
import base64
from langchain.agents import create_agent
from dotenv import load_dotenv
from embedding import search_faq
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
"""

_agent = None


_langfuse_handler = None


def _get_langfuse_handler():
    global _langfuse_handler
    if _langfuse_handler is None and os.getenv("LANGFUSE_PUBLIC_KEY"):
        from langfuse.langchain import CallbackHandler
        _langfuse_handler = CallbackHandler()
    return _langfuse_handler


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
    """Reads back the conversation so far for this session from the
    LangGraph checkpointer, in the same {role, content} shape the frontend
    uses to render chat bubbles. This is what makes switching between
    chats (or reloading the page) actually restore the conversation
    instead of showing an empty chat."""
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
    langfuse_handler = _get_langfuse_handler()

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        sentence_buffer = ""
       
        attempt_config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [h for h in [langfuse_handler] if h],
            "metadata": {"langfuse_session_id": session_id},
        }
        try:
            stream = agent.stream({"messages": messages}, config=attempt_config, stream_mode="messages")
            told_searching = False
            got_content = False
            for chunk, metadata in stream:
                if not told_searching and metadata.get("langgraph_node") == "tools":
                    yield "event: status\ndata: Searching NetSol FAQs...\n\n"
                    told_searching = True
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    got_content = True
                    yield f"event: message\ndata: {chunk.content}\n\n"
                    if want_voice_reply:
                        sentence_buffer += chunk.content
                        if re.search(r'[.!?]\s*$', sentence_buffer):
                            yield from _emit_audio_event(sentence_buffer.strip())
                            sentence_buffer = ""

            if want_voice_reply and sentence_buffer.strip():
                yield from _emit_audio_event(sentence_buffer.strip())

            if got_content:
                break  # success - no need to retry

            print(f"Model '{MODEL}' returned an empty response (attempt {attempt}/{max_attempts})")

        except Exception as e:
            print(f"Model '{MODEL}' failed (attempt {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                yield "event: message\ndata: Sorry, I'm having trouble reaching the AI provider right now. Please try again in a moment.\n\n"

    yield "event: done\ndata: [DONE]\n\n"


def _emit_audio_event(sentence_text):
  
    try:
        from TTS_services import audio as tts_audio
        audio_bytes = tts_audio(sentence_text)
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        yield f"event: audio\ndata: {b64}\n\n"
    except Exception as e:
        print(f"TTS failed for a sentence (continuing without audio for it): {e}")