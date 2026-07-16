import os
import hashlib
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from backend.config import settings

_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_fn: Optional[embedding_functions.SentenceTransformerEmbeddingFunction] = None
_collection: Optional[chromadb.Collection] = None


def _get_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
    return _chroma_client


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )
    return _embedding_fn


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name="support_docs",
            embedding_function=_get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap
    return chunks or [text]


def build_knowledge_base() -> int:
    collection = get_collection()
    kb_path = settings.knowledge_base_path
    if not os.path.isdir(kb_path):
        return 0

    total_chunks = 0
    for filename in os.listdir(kb_path):
        if not filename.endswith((".md", ".txt")):
            continue
        filepath = os.path.join(kb_path, filename)
        with open(filepath, "r") as f:
            content = f.read()
        chunks = _chunk_text(content)
        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            h = hashlib.md5(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest()
            ids.append(h)
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_index": i})
        if ids:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            total_chunks += len(ids)
    return total_chunks


def retrieve_context(query: str, n_results: int = 3) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=n_results)
    contexts = []
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            contexts.append({
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source", "unknown") if results["metadatas"][0] else "unknown",
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })
    return contexts


def get_grounded_context(ticket_text: str, n_results: int = 3) -> str:
    results = retrieve_context(ticket_text, n_results=n_results)
    if not results:
        return ""
    parts = []
    for r in results:
        if r["distance"] < 1.2:
            parts.append(f"[Source: {r['source']}]\n{r['content']}")
    return "\n\n---\n\n".join(parts) if parts else ""
