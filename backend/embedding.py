import os
from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain_chroma import Chroma
from read_data import load_and_chunk_faq
from langchain_core.tools import tool
from gcs_sync import restore_from_gcs, backup_to_gcs

load_dotenv()

restore_from_gcs()  # must run before Chroma(...) below creates its client

embeddings = init_embeddings(
    os.getenv('EMBEDDING_MODEL'),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("EMBEDDINGS_URL"),
)


vector_store = Chroma(
    collection_name="netsol_faq",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)

existing = vector_store.get()

if len(existing["ids"]) == 0:
    chunks = load_and_chunk_faq()
    vector_store.add_texts(chunks)
    print(f"Embedded {len(chunks)} chunks into Chroma.")
    backup_to_gcs()
else:
    print(f"Loaded existing collection with {len(existing['ids'])} chunks.")


@tool
def search_faq(query) :
    """Search the NetSol FAQ knowledge base for relevant information.
    Use this when the user asks about NetSol policies, internships, careers, or company information."""
    results = vector_store.similarity_search(query, k=3)
    matches = []
    for doc in results:
        content = doc.page_content
        if "Answer:" in content:
            content = content.split("Answer:", 1)[1].strip()
        matches.append(content)
    return "\n\n".join(matches)