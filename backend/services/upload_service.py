import io
import os
import chromadb
import fitz  # pymupdf
import docx
import pandas as pd
from pptx import Presentation
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"},
)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
upload_collection = chroma_client.get_or_create_collection(name="user_uploads")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def extract_text(filename, content):
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)

    elif ext == "docx":
        d = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in d.paragraphs)

    elif ext == "csv":
        df = pd.read_csv(io.BytesIO(content))
        text = df.to_string(index=False)

    elif ext == "txt":
        text = content.decode("utf-8", errors="ignore")

    elif ext == "pptx":
        prs = Presentation(io.BytesIO(content))
        slides_text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    slides_text.append(shape.text_frame.text)
        text = "\n".join(slides_text)

    else:
        return None

    return text.strip()


def store_upload(cid, filename, content):
    text = extract_text(filename, content)
    if not text:
        return 0

    chunks = splitter.split_text(text)
    ids = [f"{cid}_{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{"Cid": cid, "source": filename} for _ in chunks]
    vectors = embeddings.embed_documents(chunks)

    upload_collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=vectors,
    )
    return len(chunks)


def retrieve_relevant_uploads(cid, q, top_k=3):
    if upload_collection.count() == 0:
        return []

    query_emb = embeddings.embed_query(q)
    res = upload_collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where={"Cid": cid},
        include=["documents"],
    )
    return res["documents"][0]
