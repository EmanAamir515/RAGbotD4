import os
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv()
_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))


def audio(text, voice="aura-2-thalia-en"):
    chunks = _client.speak.v1.audio.generate(
        text=text,
        model=voice
    )
    return b"".join(chunks)