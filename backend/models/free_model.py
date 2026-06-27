
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from services.embed import retrieve_relevant_faqs
from langchain_core.tools import tool
from langchain.agents import create_agent
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

agent = create_agent(
    model=myModel,
    tools=[search_FAQs],
    system_prompt="You are a helpful NetSol support assistant. Always use search_FAQs for any question that could be about NetSol, Netsoul, netsol, or any variation of it. Never say you are unfamiliar — always search first, then answer based on results. Keep responses in plain text."
)


def ask_model_tooling(messages):
    try:
        tool_called = False
        for token, metadata in agent.stream(
            {"messages": messages},
            stream_mode="messages"
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
        
        
        

