import os
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
#MONGO_URI =" mongodb://localhost:27017"

#DB_Name = "echatbot"

FAQ_CSV_PATH = "netsol_faqs.csv"       
EMBEDDING_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
RAG_TOP_K = 2 
