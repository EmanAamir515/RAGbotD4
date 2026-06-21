import pandas as pd
import numpy as np
from config import  FAQ_CSV_PATH

def load_faqs(csv_path=FAQ_CSV_PATH):###reading .csv and chunking that data
    df = pd.read_csv(csv_path)
    
    faqs = []
    for _, row in df.iterrows():
        faqs.append({
            "question": str(row["question"]).strip(),##one chunk = one Q and its answer : row from csv
            "answer": str(row["answer"]).strip()
        })
    return faqs

