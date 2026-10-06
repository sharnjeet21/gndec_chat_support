import os
import json
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

VECTOR_DB_PATH = "backend/faiss_index"
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")
IS_E5 = "e5" in MODEL_NAME.lower()

embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

print("Loading existing FAISS index...")
vectorstore = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)

print("Loading external facts...")
with open("data/external_facts.json", "r") as f:
    facts = json.load(f)

# The new fact is the last one in the list
new_fact = facts[-1]

doc_text = f"passage: Q: {new_fact['question']}\nA: {new_fact['answer']}" if IS_E5 else f"Q: {new_fact['question']}\nA: {new_fact['answer']}"
metadata = {
    "source_file": new_fact.get("source_file", "manual"),
    "section": new_fact.get("section", ""),
    "doc_url": new_fact.get("doc_url", "")
}

print("Adding new fact to FAISS index...")
vectorstore.add_texts(texts=[doc_text], metadatas=[metadata])

print("Saving updated FAISS index...")
vectorstore.save_local(VECTOR_DB_PATH)
print("Done!")
