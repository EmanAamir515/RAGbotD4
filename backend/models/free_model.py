
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from services.embed import retrieve_relevant_faqs
from langchain_core.tools import tool
from langchain.agents import create_agent
from services.DBservices import get_checkpointer
#from openrouter import ChatOpenRouter
load_dotenv()
RAG_TOP_K = 3
myModel = ChatGroq(
    model="openai/gpt-oss-20b",##"llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
)

@tool
def search_FAQs(q: str)-> str:
    """Use this when any question regarding Netsol is asked """
    return retrieve_relevant_faqs(q,RAG_TOP_K)
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

agent = create_agent(
    model=myModel,
    tools=[search_FAQs],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=get_checkpointer()
)


def ask_model_tooling(messages,cid):
    config = {"configurable":{"thread_id":cid}}
    try:
        tool_called = False
        for token, metadata in agent.stream(
            {"messages": messages},
            stream_mode="messages",
            config=config
        ):
            if metadata.get("langgraph_node")=="tools":
                tool_called = True
                continue
            if token.content:
                yield token.content
        print(token)
        print("Tool calling was used:",tool_called)
        ##print(token.response_metadata.get("finish_reason"))##??

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Exception args:", e.args)
        if hasattr(e, "response") and e.response is not None:
            print("Status code:", e.response.status_code)
            print("Body:", e.response.text)
        
   # except Exception as e:
    #    print("Error occured in free_model => ask_model_tooling",e )
 