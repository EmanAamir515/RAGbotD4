import os
from dotenv import load_dotenv

load_dotenv()


DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
KOKORO_BASE_URL = "http://localhost:8880/v1"
KOKORO_VOICE = "af_bella"
