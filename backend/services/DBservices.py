
from pymongo import MongoClient
import os
from dotenv import load_dotenv
#from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.memory import InMemorySaver
load_dotenv()

client = MongoClient(os.getenv("MONGO_LINK"))##making connection
db = client["echatbot"]
msgs_collection = db["messages"]##like SQl table
msgs_collection.create_index("Cid")

### memory checkpoints storing in DB
## functions to store in DBs called by API endpoints
def store_msg(ci:str,r:str,c:str):
    res = msgs_collection.insert_one({"Cid":ci, "role": r, "content": c})
    return{
       "new msg added for chat id: ": str(res.inserted_id)
    } 

def get_convoHistory(cid,limit=20):## to avoid exploding graidents only limites past msgs 
    msg_list = []
    for m in msgs_collection.find({"Cid":cid}).sort("_id",-1).limit(limit):
        msg_list.append({
            "role": m["role"],
            "content": m["content"]
        })
        
    return  list(reversed(msg_list))##oldest on top 

def delete_convo(cid):
    res = msgs_collection.delete_many({"Cid": cid})
    return {"detail": f"Deleted {res.deleted_count} messages for conversation '{cid}'"}
    
def get_allconvos():
    results = msgs_collection.distinct("Cid")
    return results

_checkpointer = InMemorySaver()

def get_checkpointer():
    return _checkpointer

##def get_checkpointer():
    ##return MongoDBSaver(client, db_name="echatbot", collection_name="checkpoints")