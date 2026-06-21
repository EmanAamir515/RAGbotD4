#   uv run build_embeddings.py


from embed import build_faq_embeddings

if __name__ == "__main__":
    build_faq_embeddings()
   # build_faq_embeddings(force_rebuild=True)