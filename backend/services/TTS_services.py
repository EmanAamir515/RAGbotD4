import re
import numpy as np
import soundfile as sf
import io
from kokoro import KPipeline

pipeline = KPipeline(lang_code="a")  # load once

def audio(text, voice="af_heart"):
    """Convert one sentence of text into WAV audio bytes."""
    audio_parts = [audio for _, _, audio in pipeline(text, voice=voice)]
    combined = np.concatenate(audio_parts)
    buf = io.BytesIO()
    sf.write(buf, combined, 24000, format="WAV")
    return buf.getvalue()

def stream_with_tts(text_stream):
    """Buffer LLM tokens into sentences, speak each one as it completes."""
    buffer = ""
    for token in text_stream:
        buffer += token
        if re.search(r'[.!?]\s*$', buffer):
            yield buffer.strip(), audio(buffer.strip())
            buffer = ""
    if buffer.strip():
        yield buffer.strip(), audio(buffer.strip())