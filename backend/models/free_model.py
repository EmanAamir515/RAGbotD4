
import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from services.embed import retrieve_relevant_faqs
from langchain_core.tools import tool
from langchain.agents import create_agent
load_dotenv()
RAG_TOP_K = 3
myModel = ChatOpenRouter(
    model="openai/gpt-oss-120b:free", ##"google/gemma-4-31b-it:free"
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

@tool
def search_FAQs(q: str)-> str:
    """Use this when any question regarding Netsol is asked """
    return retrieve_relevant_faqs(q,RAG_TOP_K)

agent = create_agent(
    model=myModel,
    tools=[search_FAQs],
    system_prompt="You are a helpful assistant who if asked to answer netsol related questions Use search_FAQs"
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
            if token.content:
                yield token.content
        print(token)
        print("Tool calling was used:",tool_called)
        ##print(token.response_metadata.get("finish_reason"))##??

        
    except Exception as e:
        print("Error occured in free_model => ask_model_tooling",e )
        
        
        

