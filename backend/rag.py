import ollama
from backend.db import get_collection
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/multilingual-e5-large')


def _format_history(history: list[dict]) -> str:
    """Convert history list to a readable conversation string."""
    if not history:
        return ""
    lines = []
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


def query_rag(subject: str, question: str, history: list[dict]) -> str:
    """Search relevant chunks and query Ollama with context + history."""
    collection = get_collection()

    # Embed the question with E5 query prefix
    query_emb = model.encode(f"query: {question}").tolist()

    # Search ChromaDB filtered by subject
    try:
        if collection.count() == 0:
            return "This topic is not covered in the slides."
        results = collection.query(
            query_embeddings=[query_emb],
            where={"subject": {"$eq": subject}},
            n_results=3
        )
        chunks = results["documents"][0] if results["documents"] else []
    except Exception:
        chunks = []

    if not chunks:
        return "This topic is not covered in the slides."

    # Build context from retrieved chunks (strip the "passage: " prefix for readability)
    context_parts = [c.replace("passage: ", "", 1) for c in chunks]
    context = "\n\n---\n\n".join(context_parts)

    # Keep last 10 messages for history (sliding window)
    recent_history = history[-10:] if len(history) > 10 else history
    history_text = _format_history(recent_history)

    # Build prompt
    prompt = f"""You are an academic assistant. Answer the question based ONLY on the content below.
If the answer is not found in the content, respond with: "This topic is not covered in the slides."
Do not add any information outside the provided content.
Answer in the same language as the question.

Content:
{context}
"""

    if history_text:
        prompt += f"\nConversation history:\n{history_text}\n"

    prompt += f"\nQuestion: {question}"

    response = ollama.chat(
        model='gemma2:27b',
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response['message']['content']