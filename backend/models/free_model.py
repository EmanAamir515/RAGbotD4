import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from services.embed import retrieve_relevant_faqs
from langchain_core.tools import tool
from langchain.agents import create_agent
load_dotenv()
RAG_TOP_K = 3

# Free-tier OpenRouter models are occasionally rate-limited or return
# empty responses ("Provider returned error" upstream). These are tried
# in order; "openrouter/free" is OpenRouter's own router that
# auto-selects whichever free model is currently available, so it acts
# as a reliable last resort even if specific free model IDs change.
MODEL_CHAIN = [
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/free",
]

API_KEY = os.getenv("OPENROUTER_API_KEY")

SYSTEM_PROMPT = (
    "You are a helpful assistant.\n\n"
    "If a system message starts with '[Uploaded file: ...]', that text "
    "IS the full content of a document the user uploaded - it is already "
    "given to you directly in this conversation. When the user asks you "
    "to explain, summarize, or answer questions about that document, "
    "read and use that content directly to answer - regardless of "
    "whether the document is related to NetSol or not. Do NOT say you "
    "cannot access the file, and do NOT try to use search_FAQs for "
    "uploaded-file questions - search_FAQs is a separate tool only for "
    "looking up NetSol's general FAQ knowledge base, not for reading "
    "uploaded documents.\n\n"
    "Use search_FAQs only when the user asks a general NetSol question "
    "that is NOT about an uploaded file.\n\n"
    "Formatting rules for your responses:\n"
    "- Always use proper Markdown with real newlines between elements "
    "(never put a whole table or list on a single line).\n"
    "- For tables: put each row on its own line, starting with the "
    "header row, then a separator row (e.g. |---|---|), then each data row.\n"
    "- For lists: put each bullet or numbered item on its own line.\n"
    "- Use clear paragraph breaks (blank line) between sections.\n"
    "- Use markdown headers (##) to organize longer answers."
)


@tool
def search_FAQs(q: str)-> str:
    """Use this when any question regarding Netsol is asked """
    return retrieve_relevant_faqs(q,RAG_TOP_K)


def _build_agent(model_name):
    model = ChatOpenRouter(model=model_name, api_key=API_KEY)
    return create_agent(model=model, tools=[search_FAQs], system_prompt=SYSTEM_PROMPT)


_agents = [_build_agent(name) for name in MODEL_CHAIN]


def ask_model_tooling(messages, cid=None):
    for model_name, agent in zip(MODEL_CHAIN, _agents):
        try:
            got_content = False
            for token, metadata in agent.stream({"messages": messages}, stream_mode="messages"):
                if token.content:
                    got_content = True
                    yield token.content

            if got_content:
                return  # this model worked, we're done

            print(f"Model '{model_name}' returned an empty response, trying next model")

        except Exception as e:
            print(f"Model '{model_name}' failed: {e}")

    yield "Sorry, I'm having trouble reaching the AI provider right now. Please try again in a moment."