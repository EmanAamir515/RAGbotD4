import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from embedding import search_faq

load_dotenv()

llm = ChatOpenRouter(
    model=os.getenv("MODEL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
)

llm_with_tools = llm.bind_tools([search_faq])
response = llm_with_tools.invoke("how many clients does netsol have")

print("TOOL CALLS:", response.tool_calls)
print("CONTENT:", response.content)