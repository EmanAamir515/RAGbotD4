import chromadb
import pandas as pd
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
RAG_TOP_K = 3
load_dotenv()
embeddings = OpenAIEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",  
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    check_embedding_ctx_length=False,   
    #encoding_format="float",
    model_kwargs={"encoding_format": "float"},  
)

chroma_client = chromadb.PersistentClient(path= "./chroma_db")
collection = chroma_client.get_or_create_collection(name= "netsol_faqs" )


def retrieve_relevant_faqs(q, top_k= RAG_TOP_K):
    if collection.count() == 0:
        return []
    
    query_emb = embeddings.embed_query(q)
    res = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        include=["metadatas","distances"]
    )
    matches = []
    
    for m in res["metadatas"][0]:
        matches.append(
            {
                "question" : m["question"],
                "answer": m["answer"]
            }
        )
    return matches
        
        
    
    
def load_faqs(csv_path= "data/netsol_faqs.csv"):###reading .csv and chunking that data
    df = pd.read_csv(csv_path)
    
    faqs = []
    for row in range(len(df)):
        faqs.append({
            "question": df["question"][row],
            "answer": df["answer"][row]
        })
    return faqs

def build_faq_embeddings(force_rebuild=False):
    count = collection.count()
    if count > 0 and force_rebuild != True:
        print("chroma already has chunks",count)
        return
    #if count > 0 and force_rebuild == True: clearinf old chunks from collection
    
    faqs = load_faqs()
    if not faqs:
        print("No FAQ data found check path")
        return
    
    ids = []
    docs = []
    metadatas = []
    
    for i in range (len(faqs)):
        ids.append(str(i))
    for f in faqs:
        docs.append(f["question"])
        metadatas.append( {"question": f["question"],
                     "answer": f["answer"]})
        
    vectors = embeddings.embed_documents(docs)

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metadatas,
        embeddings=vectors,
    )
    print(f"Stored {len(faqs)} FAQ chunks in ChromaDB at './chroma_db'.")

    from services.gcs_sync import backup_to_gcs
    backup_to_gcs()
