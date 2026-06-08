"""
generate.py — The Unofficial Guide to MNSU Professors
Generates grounded, cited answers using retrieved chunks + Groq API.

Usage:
    python generate.py "What do students say about John Burke?"
    python generate.py "Is Mark Hall a good professor?"

Requires:
    pip install groq
    Set environment variable: GROQ_API_KEY=your_key_here
"""

import os
import sys
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
from retrieve import retrieve

# ── Config ────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 500
MIN_CHUNKS_FOR_CONFIDENCE = 3  # warn if fewer chunks retrieved

SYSTEM_PROMPT = """You are The Unofficial Guide to MNSU Professors — a helpful assistant that answers questions about professors at Minnesota State University, Mankato using only student reviews provided to you.

Rules you must follow:
1. Answer ONLY using the review excerpts provided in the context below. Do not use outside knowledge.
2. Every claim you make must be traceable to a specific review. Cite the professor name and rating (e.g., "One student (4/5) said...").
3. If the reviews are mixed, reflect that honestly — do not pick a side.
4. If fewer than 3 reviews are provided, say: "Note: only a small number of reviews are available for this professor, so this answer may not be representative."
5. If no relevant reviews are provided, say: "I don't have enough information in my documents to answer that question."
6. Do not make up quotes, ratings, or professor names not present in the context.
7. Keep answers concise — 3 to 6 sentences unless the question requires more detail."""


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for the prompt."""
    if not chunks:
        return "No relevant reviews found."
    lines = ["Here are the student reviews relevant to this question:\n"]
    for i, c in enumerate(chunks, 1):
        lines.append(f"Review {i}:\n{c['text']}\n")
    return "\n".join(lines)


def generate(query: str, professor: str = None, department: str = None) -> dict:
    """
    Full RAG pipeline: retrieve → generate.

    Returns:
        {
            "query":    str,
            "answer":   str,
            "chunks":   list[dict],
            "warned":   bool,
        }
    """
    chunks = retrieve(query, professor=professor, department=department)
    warned = len(chunks) < MIN_CHUNKS_FOR_CONFIDENCE

    context = build_context(chunks)
    user_message = f"{context}\n\nQuestion: {query}"

    client = Groq()  # reads GROQ_API_KEY from environment
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )

    answer = response.choices[0].message.content.strip()

    return {
        "query":  query,
        "answer": answer,
        "chunks": chunks,
        "warned": warned,
    }


def print_result(result: dict):
    """Pretty-print a generate() result."""
    print(f"Question: {result['query']}")
    print("─" * 60)
    print(result["answer"])
    print()
    if result["warned"]:
        print(f"⚠  Only {len(result['chunks'])} chunk(s) retrieved — answer may be limited.")
    print(f"Sources: {', '.join(set(c['source_file'] for c in result['chunks']))}")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Who is the best professor at MNSU?"
    result = generate(query)
    print_result(result)
