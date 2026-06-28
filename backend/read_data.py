import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_chunks(pair):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_text(pair)

def load_and_chunk_faq():
    df = pd.read_csv("./data/netsol_faq.csv")
    all_chunks = []

    for index, row in df.iterrows():
        pair = f"Question: {row['question']} \nAnswer: {row['answer']}"
        sub_chunks = get_chunks(pair)
        all_chunks.extend(sub_chunks)

    return all_chunks