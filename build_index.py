import os
import glob
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from google import genai
from google.genai.types import EmbedContentConfig

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


class GeminiEmbeddings(Embeddings):
    """
    A thin adapter so LangChain's FAISS vectorstore can call Gemini's
    embedding model. LangChain doesn't know anything about Gemini by
    default — this class is the translation layer: LangChain calls
    embed_documents()/embed_query(), and we implement those by calling
    google-genai's embed_content() underneath.
    """

    def embed_documents(self, texts):
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768,
            ),
        )
        return [e.values for e in result.embeddings]

    def embed_query(self, text):
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        return result.embeddings[0].values


def main():
    docs_text = []
    for path in glob.glob("runbooks/*.md"):
        with open(path) as f:
            docs_text.append(f.read())

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents(docs_text)
    print(f"Split runbook corpus into {len(chunks)} chunks")

    embeddings = GeminiEmbeddings()
    index = FAISS.from_documents(chunks, embeddings)
    index.save_local("faiss_index")
    print("Saved FAISS index to ./faiss_index")


if __name__ == "__main__":
    main()
