import os
from dotenv import load_dotenv
from deepgram import DeepgramClient
load_dotenv()

_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))

def STT_function(audio_bytes: bytes) -> str:
    try:
        response = _client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-3",
        )
        return response.results.channels[0].alternatives[0].transcript

    except Exception as e:
        print(f"Exception: {e}")
        return ""
