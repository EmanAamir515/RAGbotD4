import os
from dotenv import load_dotenv
from deepgram import DeepgramClient
load_dotenv()

DeepgramClient = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))

def STT_function(audio_bytes:bytes)-> str:
    try:
        response = DeepgramClient.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-3",
           # smart_format=True,
        )
        print(f"response: {response}\n\n")
        return response.results.channels[0].alternatives[0].transcript  # ✅ string

        #return response.results.channels[0].alternatives[0].transcript

    except Exception as e:
        print(f"Exception: {e}")
        return ""

