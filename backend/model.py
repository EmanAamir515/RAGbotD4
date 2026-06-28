from pydantic import BaseModel

# NOTE: /chat now accepts multipart Form fields (it also takes an optional
# file upload), not a JSON body, so this is no longer used as the request
# model for that endpoint. Kept for reference/any future JSON-only routes.
class ChatRequest(BaseModel):
      message:str
      session_id:str