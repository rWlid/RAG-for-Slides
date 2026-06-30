import chromadb

# Initialize local persistent ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="slides")


def get_collection():
    return collection


def get_client():
    return client