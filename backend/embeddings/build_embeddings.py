#   uv run build_embeddings.py
from services.embed import build_faq_embeddings

if __name__ == "__main__":
    build_faq_embeddings()
