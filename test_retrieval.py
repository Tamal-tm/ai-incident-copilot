# test_retrieval.py
import os
from langchain_community.vectorstores import FAISS
from build_index import GeminiEmbeddings

embeddings = GeminiEmbeddings()
index = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

results = index.similarity_search("HighErrorBudgetBurn service-a 5xx errors", k=2)
for r in results:
    print("---")
    print(r.page_content)
