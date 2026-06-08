"""
retrieve.py — The Unofficial Guide to MNSU Professors
Semantic search over the ChromaDB collection with optional metadata filtering.

Usage (as a module):
    from retrieve import retrieve
    chunks = retrieve("What do students say about John Burke?", professor="John Burke")

Usage (interactive test):
    python retrieve.py "Is Mark Hall a good professor?"
"""

import sys
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "mnsu_professors"

# Load once at module level so repeated calls don't reload
_model = None
_collection = None


def _load():
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(COLLECTION_NAME)


def retrieve(
    query: str,
    professor: str = None,
    department: str = None,
    k: int = 5,
) -> list[dict]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        query:       Natural language question.
        professor:   Optional — filter to chunks from this professor only.
        department:  Optional — filter to chunks from this department only.
        k:           Number of chunks to return (default 5).

    Returns:
        List of dicts with keys: text, professor_name, department,
        source_type, rating, difficulty, course, source_file, distance.
    """
    _load()

    # Build optional metadata filter
    where = None
    if professor and department:
        where = {"$and": [
            {"professor_name": {"$eq": professor}},
            {"department": {"$eq": department}},
        ]}
    elif professor:
        where = {"professor_name": {"$eq": professor}}
    elif department:
        where = {"department": {"$eq": department}}

    # Embed the query
    query_embedding = _model.encode([query]).tolist()

    # Query ChromaDB
    kwargs = {
        "query_embeddings": query_embedding,
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = _collection.query(**kwargs)

    # Flatten results into a list of dicts
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":           doc,
            "professor_name": meta.get("professor_name", "N/A"),
            "department":     meta.get("department", "N/A"),
            "source_type":    meta.get("source_type", "N/A"),
            "rating":         meta.get("rating", -1.0),
            "difficulty":     meta.get("difficulty", -1.0),
            "course":         meta.get("course", "N/A"),
            "source_file":    meta.get("source_file", "N/A"),
            "distance":       dist,
        })

    return chunks


def format_chunks_for_display(chunks: list[dict]) -> str:
    """Pretty-print retrieved chunks for debugging."""
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"── Chunk {i} (distance: {c['distance']:.4f}) ──")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Who is the best professor?"
    print(f"Query: {query}\n")
    chunks = retrieve(query)
    print(format_chunks_for_display(chunks))
