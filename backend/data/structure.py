from pydantic import BaseModel

##payload schema
class mem(BaseModel):##this class defines structure of our data (its variables)
    Cid: str
    role: str
    content: str
