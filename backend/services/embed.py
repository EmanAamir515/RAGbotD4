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
    
    


    

    
        
    








# # embedding via openrouter , vectorDB chroma and topKresults
# import requests
# import chromadb
# from .rag import load_faqs
# from data.config import OPENROUTER_API_KEY, EMBEDDING_MODEL, FAQ_CSV_PATH, RAG_TOP_K
# _session = requests.Session() 

# chroma_client = chromadb.PersistentClient(path= "./chroma_db")
# collection = chroma_client.get_or_create_collection(name= "netsol_faqs" )##bucket of vectors+their metadata

# def embed_text(text):
#     response = _session.post(
#         url="https://openrouter.ai/api/v1/embeddings",
#         headers={
#             "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#             "Content-Type": "application/json"
#         },
#         json={
#             "model": EMBEDDING_MODEL,
#             "input": [text],
#             "encodingFormat": "float"
#         },
#         timeout=15
#     )
#     if response.status_code != 200:
#         raise Exception(f"Embedding API error: {response.status_code} - {response.text}")
#     data = response.json()
#     return data["data"][0]["embedding"]#vector

# def build_faq_embeddings(force_rebuild=False):
#     existing_count = collection.count()

#     if existing_count > 0 and not force_rebuild:
#         print(f"Chroma collection already has {existing_count} chunks - skipping rebuild.")
#         return

#     if existing_count > 0 and force_rebuild: ##if already avaible no need to make again
#         all_ids = collection.get()["ids"]
#         if all_ids:
#             collection.delete(ids=all_ids)
#         print(f"Cleared {len(all_ids)} old chunks from collection")

#     faqs = load_faqs()
#     if not faqs:
#         print("No FAQ data loaded check FAQ_CSV_PATH!!")
#         return

#     ids = [str(i) for i in range(len(faqs))]##rows in csv
#     documents = [f["question"] for f in faqs] ##question text thats get searched
#     metadatas = [{"question": f["question"], "answer": f["answer"]} for f in faqs]## what we get back if matched 
#     embeddings = [embed_text(f["question"]) for f in faqs]
# ## building vector Base
#     collection.add( 
#         ids=ids,
#         documents=documents,
#         metadatas=metadatas,
#         embeddings=embeddings,
#     )
#     print(f"Stored {len(faqs)} FAQ chunks in ChromaDB at '{"./chroma_db"}'.")


# def retrieve_relevant_faqs(query, top_k=RAG_TOP_K):
    
#     if collection.count() == 0:
#         return []

#     query_emb = embed_text(query)##user query 
#     results = collection.query(
#         query_embeddings=[query_emb],##checking similarity of both vectors
#         n_results=top_k,
#         include=["metadatas", "distances"],#finding top 2 
#     )

#     matches = []
#     for meta in results["metadatas"][0]:##for only first query single
#         matches.append({"question": meta["question"], "answer": meta["answer"]})
#     return matches
    
