
import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from services.embed import retrieve_relevant_faqs
from langchain_core.tools import tool
from langchain.agents import create_agent
load_dotenv()
myModel = ChatOpenRouter(
    model="openai/gpt-oss-120b:free", ##"google/gemma-4-31b-it:free"
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

@tool
def search_FAQs(q: str)-> str:
    """Use this when any question regarding Netsol is asked """
    return retrieve_relevant_faqs(q,os.getenv("RAG_TOP_K"))

agent = create_agent(
    model=myModel,
    tools=[search_FAQs],
    system_prompt="You are a helpful assistant who if asked to answer netsol related questions Use search_FAQs"
)


def ask_model_tooling(messages):
    try:
        for token, metadata in agent.stream(
            {"messages": messages},
            stream_mode="messages"
        ):
            if token.content:
                yield token.content
        print(token)
        print(token.response_metadata.get("finish_reason"))##??

        
    except Exception as e:
        print("Error occured in free_model => ask_model_tooling",e )
        
        
        

