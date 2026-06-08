"""
ingest.py — The Unofficial Guide to MNSU Professors
Reads all .txt files from /docs/, chunks them, embeds with all-MiniLM-L6-v2,
and upserts into a local ChromaDB collection.

Usage:
    python ingest.py

Requirements:
    pip install sentence-transformers chromadb
"""

import os
import re
import uuid
import chromadb
from dotenv import load_dotenv
load_dotenv()
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
DOCS_DIR = "documents"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "mnsu_professors"
MIN_REDDIT_CHARS = 80  # filter out short Reddit comments with no signal

# Maps filename stems to (professor_name, department, source_type)
FILE_METADATA = {
    "rmp_burke_john":       ("John Burke",     "Information Technology", "rmp_review"),
    "rmp_bates_rebecca":    ("Rebecca Bates",  "Computer Science",       "rmp_review"),
    "rmp_habib_abo":        ("Abo Habib",       "Accounting",             "rmp_review"),
    "rmp_smith_steven":     ("Steven Smith",   "Theater",                "rmp_review"),
    "rmp_page_scott":       ("Scott Page",     "Education",              "rmp_review"),
    "rmp_romero_marino":    ("Marino Romero",  "Mathematics",            "rmp_review"),
    "rmp_hall_mark":        ("Mark Hall",      "Marketing",              "rmp_review"),
    "rmp_kim_in_jae":       ("In-Jae Kim",     "Mathematics",            "rmp_review"),
    "rmp_school_mnsu":      ("N/A",            "N/A",                    "rmp_school"),
    "aggregator_mnsu":      ("N/A",            "N/A",                    "aggregator"),
    "reddit_mnsu_professor_advice": ("N/A",   "N/A",                    "reddit"),
    "reddit_mnsu_cs_courses":       ("N/A",   "N/A",                    "reddit"),
}

# Tags that appear in RMP reviews — strip these from chunk text
RMP_TAG_PATTERNS = [
    r"^(Tough grader|Get ready to read|Test heavy|Lots of homework|Amazing lectures|"
    r"Gives good feedback|Caring|Accessible outside class|Participation matters|"
    r"Clear grading criteria|Group projects|EXTRA CREDIT|Graded by few things|"
    r"Skip class\? You won't pass\.|Lecture heavy|So many papers)$",
    r"^(Helpful|Thumbs up|Thumbs down)$",
    r"^\d+$",  # standalone numbers (thumbs up/down counts)
    r"^Computer Icon.*",  # RMP UI artifacts
]


def is_tag_line(line: str) -> bool:
    """Return True if this line is an RMP tag or UI artifact to strip."""
    for pattern in RMP_TAG_PATTERNS:
        if re.match(pattern, line.strip()):
            return True
    return False


def parse_rmp_review_block(block: str) -> dict | None:
    """
    Parse one RMP review block into {text, rating, course, difficulty}.
    Block format:
        Quality
        4.0
        Difficulty
        5.0
        ACCT301
        Oct 3rd, 2025
        For Credit: Yes
        ...
        <review text>
        <tags>
    Returns None if no review text found.
    """
    lines = [l.strip() for l in block.strip().splitlines()]

    rating = None
    difficulty = None
    course = None
    review_lines = []

    i = 0
    # Parse structured header fields
    while i < len(lines):
        line = lines[i]
        if line == "Quality" and i + 1 < len(lines):
            try:
                rating = float(lines[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if line == "Difficulty" and i + 1 < len(lines):
            try:
                difficulty = float(lines[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        # Course code: all-caps word like ACC300, ACCT301, CS101
        if re.match(r"^[A-Z]{2,6}\d{3,4}$", line):
            course = line
            i += 1
            continue
        # Skip known metadata lines
        if any(line.startswith(prefix) for prefix in [
            "For Credit:", "Attendance:", "Grade:", "Textbook:",
            "Online Class:", "Would Take Again:", "Jan ", "Feb ", "Mar ",
            "Apr ", "May ", "Jun ", "Jul ", "Aug ", "Sep ", "Oct ", "Nov ", "Dec ",
        ]):
            i += 1
            continue
        # Skip tag lines
        if is_tag_line(line):
            i += 1
            continue
        # Non-empty lines at this point are review text
        if line:
            review_lines.append(line)
        i += 1

    review_text = " ".join(review_lines).strip()
    if not review_text or len(review_text) < 20:
        return None

    return {
        "review_text": review_text,
        "rating": rating,
        "difficulty": difficulty,
        "course": course or "N/A",
    }


def chunk_text(filepath: str) -> list[dict]:
    """
    Split a .txt file into chunks. Returns a list of dicts:
        {
            "text":           str,   # chunk text with context header prepended
            "professor_name": str,
            "department":     str,
            "source_type":    str,   # rmp_review | rmp_school | aggregator | reddit
            "rating":         float | None,
            "difficulty":     float | None,
            "course":         str,
            "source_url":     str,
            "source_file":    str,
        }
    """
    stem = os.path.splitext(os.path.basename(filepath))[0]
    meta = FILE_METADATA.get(stem, ("Unknown", "Unknown", "rmp_review"))
    professor_name, department, source_type = meta

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Strip the header comment block (lines starting with #)
    lines = raw.splitlines()
    content_lines = [l for l in lines if not l.startswith("#")]
    content = "\n".join(content_lines)

    chunks = []

    if source_type == "rmp_review" or source_type == "rmp_school":
        # Split on double newlines — each block is one review
        blocks = re.split(r"\n{2,}", content)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            parsed = parse_rmp_review_block(block)
            if parsed is None:
                continue

            rating_str = f"{parsed['rating']}/5" if parsed["rating"] is not None else "N/A"
            header = f"[Professor: {professor_name} | Dept: {department} | Rating: {rating_str} | Course: {parsed['course']}]"
            full_text = f"{header}\n{parsed['review_text']}"

            chunks.append({
                "text": full_text,
                "professor_name": professor_name,
                "department": department,
                "source_type": source_type,
                "rating": parsed["rating"],
                "difficulty": parsed["difficulty"],
                "course": parsed["course"],
                "source_file": stem,
            })

    elif source_type == "reddit":
        # Split on double newlines — each block is one comment
        blocks = re.split(r"\n{2,}", content)
        for block in blocks:
            block = block.strip()
            if not block or len(block) < MIN_REDDIT_CHARS:
                continue  # filter short noise comments
            header = f"[Source: Reddit r/MNSU | Type: student discussion]"
            full_text = f"{header}\n{block}"
            chunks.append({
                "text": full_text,
                "professor_name": "N/A",
                "department": "N/A",
                "source_type": source_type,
                "rating": None,
                "difficulty": None,
                "course": "N/A",
                "source_file": stem,
            })

    elif source_type == "aggregator":
        # Each non-empty line is one entry
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            chunks.append({
                "text": f"[Source: RMP Aggregator | School: MNSU]\n{line}",
                "professor_name": "N/A",
                "department": "N/A",
                "source_type": source_type,
                "rating": None,
                "difficulty": None,
                "course": "N/A",
                "source_file": stem,
            })

    return chunks


def ingest_all():
    """Read all .txt files in DOCS_DIR, chunk them, embed, and upsert into ChromaDB."""

    # Load embedding model
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Set up ChromaDB
    print(f"Connecting to ChromaDB at '{CHROMA_DIR}'...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection so re-runs are clean
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'.")
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks = []

    # Load and chunk every .txt file
    txt_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]
    if not txt_files:
        print(f"No .txt files found in '{DOCS_DIR}'. Add your review files first.")
        return

    for filename in sorted(txt_files):
        filepath = os.path.join(DOCS_DIR, filename)
        chunks = chunk_text(filepath)
        print(f"  {filename}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No chunks produced. Check that your .txt files are populated.")
        return

    print(f"\nTotal chunks: {len(all_chunks)}")
    print("Embedding and upserting into ChromaDB...")

    # Embed in one batch for efficiency
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Upsert into ChromaDB
    ids = [str(uuid.uuid4()) for _ in all_chunks]
    metadatas = [
        {
            "professor_name": c["professor_name"],
            "department":     c["department"],
            "source_type":    c["source_type"],
            "rating":         c["rating"] if c["rating"] is not None else -1.0,
            "difficulty":     c["difficulty"] if c["difficulty"] is not None else -1.0,
            "course":         c["course"],
            "source_file":    c["source_file"],
        }
        for c in all_chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"\nDone. {len(all_chunks)} chunks stored in ChromaDB collection '{COLLECTION_NAME}'.")
    print(f"Database saved to '{CHROMA_DIR}/'.")


if __name__ == "__main__":
    ingest_all()
