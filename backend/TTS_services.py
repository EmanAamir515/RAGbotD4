import re
import numpy as np
import soundfile as sf
import io
from kokoro import KPipeline

_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = KPipeline(lang_code="a")
    return _pipeline


def audio(text, voice="af_heart"):
    """Convert one sentence of text into WAV audio bytes"""
    pipeline = _get_pipeline()
    audio_parts = [piece for _, _, piece in pipeline(text, voice=voice)]
    if not audio_parts:
        raise ValueError(f"Kokoro produced no audio for the given text: {text!r}")
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