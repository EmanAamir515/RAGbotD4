
import requests
import json
from config import OPENROUTER_API_KEY

def ask_model_stream(messages):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY }",
            "Content-Type": "application/json"
        },
        json={
            "model":"openai/gpt-oss-120b:free",##"google/gemma-4-31b-it:free",###openai/gpt-oss-120b:free"
            "messages": messages,
            "stream": True # Enable streaming from the model
        },
        stream=True
    )
    print("status code stream:",response.status_code)
   
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if not decoded_line.startswith('data: '):  
                continue
            decoded_line = decoded_line[6:]  # slice exactly 6 chars: "data: "
            if decoded_line.strip() == "[DONE]":
                break
            try:
                chunk_json = json.loads(decoded_line)
                chunk_text = chunk_json["choices"][0]["delta"].get("content", "")
                if chunk_text:
                    yield chunk_text
            except Exception:
                continue
            
            
# def ask_model(messages):
    
#     response = requests.post(
#         url = "https://openrouter.ai/api/v1/chat/completions",
        
#         headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY }",
#         "Content-Type": "application/json"
#         },
        
#         json={
#         "model": "openrouter/free",
#         "messages": messages
#         }
#     )
    
#     print("status code:",response.status_code)

#     result = response.json()

#     return result["choices"][0]["message"]["content"]