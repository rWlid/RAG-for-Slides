from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from backend.db import get_collection
from sentence_transformers import SentenceTransformer
import os
import hashlib

model = SentenceTransformer('intfloat/multilingual-e5-large')


def ingest_md(file_path: str, subject: str):
    """Read, chunk, embed, and store an MD file into ChromaDB."""
    collection = get_collection()

    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    filename = os.path.basename(file_path)

    # Remove existing chunks for this file+subject to avoid duplicates
    try:
        existing = collection.get(where={"$and": [{"subject": {"$eq": subject}}, {"filename": {"$eq": filename}}]})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    # Stage 1: Split by markdown headers
    headers_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
    )
    header_chunks = headers_splitter.split_text(md_content)

    # Stage 2: Apply overlap to keep context continuity
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    final_chunks = text_splitter.split_documents(header_chunks)

    if not final_chunks:
        return 0

    # Embed and store
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(final_chunks):
        content = f"passage: {chunk.page_content}"
        embedding = model.encode(content).tolist()

        # Stable ID based on content hash to avoid duplicates
        chunk_id = hashlib.md5(f"{subject}_{filename}_{i}".encode()).hexdigest()

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(content)
        metadatas.append({
            "subject": subject,
            "filename": filename,
            "h1": chunk.metadata.get("h1", ""),
            "h2": chunk.metadata.get("h2", ""),
            "h3": chunk.metadata.get("h3", ""),
        })

    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return len(final_chunks)


def delete_subject(subject: str):
    """Delete all chunks belonging to a subject."""
    collection = get_collection()
    try:
        existing = collection.get(where={"subject": subject})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
        return True
    except Exception:
        return False


def list_subjects() -> list[str]:
    """Return a sorted list of all distinct subject names."""
    collection = get_collection()
    try:
        result = collection.get(include=["metadatas"])
        subjects = sorted(set(m["subject"] for m in result["metadatas"] if "subject" in m))
        return subjects
    except Exception:
        return []