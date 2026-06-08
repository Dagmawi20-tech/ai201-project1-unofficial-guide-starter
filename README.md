# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

Student reviews of professors and courses at Minnesota State University, Mankato (MNSU). This knowledge is valuable because it captures what students actually experience — teaching quality, grading behavior, exam difficulty, and workload reality — none of which appears in official course catalogs or department websites. It is hard to find through official channels because it is scattered across Rate My Professors, Reddit threads, and student forums, written in inconsistent formats, and impossible to query in natural language. There is no single place where an MNSU student can ask "which professor actually explains things well?" and get a grounded, sourced answer drawn from real peer experiences.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Rate My Professors — John Burke | RMP review page | https://www.ratemyprofessors.com/professor/2555592 / `documents/rmp_burke_john.txt` |
| 2 | Rate My Professors — Rebecca Bates | RMP review page | https://www.ratemyprofessors.com/professor/625846 / `documents/rmp_bates_rebecca.txt` |
| 3 | Rate My Professors — Abo Habib | RMP review page | https://www.ratemyprofessors.com/professor/361747 / `documents/rmp_habib_abo.txt` |
| 4 | Rate My Professors — Steven Smith | RMP review page | https://www.ratemyprofessors.com/search/professors/559?q=Steven+Smith / `documents/rmp_smith_steven.txt` |
| 5 | Rate My Professors — Scott Page | RMP review page | https://www.ratemyprofessors.com/search/professors/559?q=Scott+Page / `documents/rmp_page_scott.txt` |
| 6 | Rate My Professors — Marino Romero | RMP review page | https://www.ratemyprofessors.com/professor/3131109 / `documents/rmp_romero_marino.txt` |
| 7 | Rate My Professors — Mark Hall | RMP review page | https://www.ratemyprofessors.com/professor/501100 / `documents/rmp_hall_mark.txt` |
| 8 | Rate My Professors — In-Jae Kim | RMP review page | https://www.ratemyprofessors.com/professor/926604 / `documents/rmp_kim_in_jae.txt` |
| 9 | Rate My Professors — MNSU school page | RMP school page | https://www.ratemyprofessors.com/school/559 / `documents/rmp_school_mnsu.txt` |
| 10 | RMP aggregator — ratemyprofessors.io | Aggregator listing | https://ratemyprofessors.io/minnesota-state-university-mankato / `documents/aggregator_mnsu.txt` |

---

## Chunking Strategy

**Chunk size:** One review = one chunk. RMP reviews range from approximately 80–200 tokens. No fixed character limit was used — chunk boundaries follow natural review boundaries (blank lines between reviews in the `.txt` files).

**Overlap:** None for RMP reviews. Each review is a self-contained student opinion, so overlapping chunks would mix quotes from different students and make source attribution ambiguous. A 30-token overlap was planned for Reddit comments to preserve cross-comment context, but Reddit files were empty so this was not used in practice.

**Why these choices fit your documents:** RMP reviews are short and self-contained — each one expresses a complete opinion about a specific professor. Splitting a review mid-sentence would destroy its meaning, and merging multiple reviews into one chunk would make it impossible to attribute any claim to a specific student's rating. The 1-review-1-chunk approach also makes metadata attachment clean: every chunk carries professor name, department, rating, and source file without ambiguity. Before chunking, the parser strips RMP metadata lines (Quality, Difficulty, course date, attendance, grade fields) and tag lines (e.g. "Tough grader", "Get ready to read") so that only the actual review text is embedded. Each chunk is also prepended with a context header: `[Professor: X | Dept: Y | Rating: Z/5 | Course: N]`.

**Final chunk count:** 177 chunks total across all files (Habib: 10, Hall: 10, Kim: 10, Page: 10, Smith: 10, Bates: 9, Burke: 9, Romero: 7, school: 6, aggregator: 96).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. Chosen because it runs locally with no API key required, is free, has a 256-token max input that fits all review chunks without truncation, and performs well on short opinionated text. The model produces 384-dimensional vectors stored in a local ChromaDB collection with cosine similarity search.

**Production tradeoff reflection:** If cost were no constraint, I would weigh three tradeoffs. First, `text-embedding-3-large` (OpenAI) offers higher accuracy on nuanced semantic distinctions — for example, distinguishing "good at giving feedback" from "good at lecturing" — but requires an API key and costs per token. Second, `multilingual-e5-large` would better handle international student reviews that mix English with another language, which is relevant at MNSU given its large international student population. Third, for a deployed system I would consider API-hosted embeddings to avoid the cold-start latency of loading a local model on each server restart, even though latency is not critical for a query interface (as opposed to real-time autocomplete).

---

## Grounded Generation

**System prompt grounding instruction:** The system prompt given to the model reads:

> "You are The Unofficial Guide to MNSU Professors — a helpful assistant that answers questions about professors at Minnesota State University, Mankato using only student reviews provided to you.
>
> Rules you must follow:
> 1. Answer ONLY using the review excerpts provided in the context below. Do not use outside knowledge.
> 2. Every claim you make must be traceable to a specific review. Cite the professor name and rating (e.g., 'One student (4/5) said...').
> 3. If the reviews are mixed, reflect that honestly — do not pick a side.
> 4. If fewer than 3 reviews are provided, say: 'Note: only a small number of reviews are available for this professor, so this answer may not be representative.'
> 5. If no relevant reviews are provided, say: 'I don't have enough information in my documents to answer that question.'
> 6. Do not make up quotes, ratings, or professor names not present in the context.
> 7. Keep answers concise — 3 to 6 sentences unless the question requires more detail."

**How source attribution is surfaced in the response:** Every retrieved chunk is prepended with a context header containing the professor name and rating before being passed to the model. The system prompt instructs the model to cite professor name and rating inline for every claim (e.g. "One student (4/5) said..."). The `generate()` function also prints the source filenames at the end of every response so the user can trace which documents were used.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do students say about John Burke's teaching style? | Must reference Burke, mention practical/applied coding, cite positive review, not reference other professors. | Cited multiple Burke reviews praising hands-on coding approach and industry prep; included one negative view; stayed on Burke only. | Relevant | Accurate |
| 2 | Is Mark Hall a good professor? | Must reflect low rating (1.8/5) and negative sentiment. Must NOT say he is good. Should cite specific complaints. | Reflected mostly negative sentiment with specific complaints (no feedback, confusing lectures, unfair grading); one positive view noted; did not claim he is good. | Relevant | Partially accurate |
| 3 | Which math professor at MNSU has the best student ratings? | Must name Marino Romero (4.3/5) or In-Jae Kim. Must not hallucinate. | Named both Romero and Kim with 5/5 ratings from retrieved reviews; no hallucinated professors. | Relevant | Accurate |
| 4 | What do students say about Abo Habib's exams? | Must cite specific exam difficulty observations from Habib reviews. | Cited tough exams, textbook reliance, confusing formatting across exams and lectures; specific and grounded. | Relevant | Accurate |
| 5 | Who is the most beloved professor at MNSU according to student reviews? | Must name Steven Smith (4.7/5, 110 ratings, 100% would take again) and cite rating/count. | Correctly named Steven Smith and cited specific positive reviews; did not cite his overall 4.7/5 rating or 110-review count. | Relevant | Partially accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "Who is the most beloved professor at MNSU according to student reviews?" (Question 5)

**What the system returned:** The system correctly named Steven Smith and cited positive individual reviews, but failed to mention his overall rating (4.7/5) or his review count (110 ratings, 100% would take again) — the two strongest pieces of evidence that he is the most beloved professor at MNSU.

**Root cause (tied to a specific pipeline stage):** The root cause is a mismatch between source types at the chunking and retrieval stages. The aggregator file (`aggregator_mnsu.txt`) stores overall scores as structured rows (e.g. "Steven Smith | Theater | 4.7 | 110 ratings"), but these rows were chunked as plain text lines with no professor-specific context header. When the query "most beloved professor" was embedded and compared to chunks, the semantic similarity favored narrative review text over the dry aggregator rows — so the aggregator chunk containing Smith's 4.7/5 score ranked below the review text chunks and was not retrieved in the top 5. The model then answered from review text alone, which does not contain the aggregate statistics.

**What you would change to fix it:** Reformat aggregator chunks to include a natural language summary rather than a raw data row — for example: "Steven Smith (Theater) has an overall rating of 4.7/5 based on 110 student ratings, with 100% of students saying they would take his class again." This phrasing would embed close to queries about highly-rated or beloved professors and would surface in retrieval alongside the review text chunks.

---

## Spec Reflection

**One way the spec helped you during implementation:** The chunking strategy section of `planning.md` directly shaped how `ingest.py` was written. Because the spec stated "1 review = 1 chunk" and explained that splitting reviews would destroy meaning and make citation ambiguous, the implementation used blank-line boundaries rather than a fixed character count. Without that decision documented in advance, it would have been easy to default to a fixed 500-character split, which would have cut reviews mid-sentence and mixed metadata lines into chunk text.

**One way your implementation diverged from the spec, and why:** The spec planned for Reddit threads as sources (two files, `reddit_mnsu_professor_advice.txt` and `reddit_mnsu_cs_courses.txt`) with a 30-token overlap strategy for comments. In practice, no relevant Reddit threads were found for MNSU professors, so both files remained empty and the Reddit chunking logic was never exercised. The final corpus relied entirely on RMP reviews and the aggregator, which still met the 10-source requirement. The spec's anticipated challenge about "thin corpus" also proved accurate — Marino Romero only produced 7 chunks, which was enough but limited the depth of answers about him.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* The Chunking Strategy and Documents sections of `planning.md`, plus a sample `.txt` file (`rmp_habib_abo.txt`) showing the exact RMP format with Quality/Difficulty/tag lines mixed in with review text.
- *What it produced:* A complete `ingest.py` with a `parse_rmp_review_block()` function that strips metadata lines (Quality, Difficulty, course codes, dates, attendance fields) and tag lines (Tough grader, Get ready to read, etc.), then extracts only the review text and prepends a context header. It also produced `chunk_text()`, `ingest_all()`, and ChromaDB upsert logic.
- *What I changed or overrode:* The initial version used `docs/` as the document directory. I directed Claude to change it to `documents/` to match the starter repo's actual folder name. I also directed it to add `python-dotenv` support so the Groq API key could be loaded from the `.env` file the starter kit provided.

**Instance 2**

- *What I gave the AI:* The Evaluation Plan section of `planning.md` with the 5 test questions and expected answers, plus the Retrieval Approach section specifying the Groq API and `llama-3.3-70b-versatile` model.
- *What it produced:* `generate.py` with a system prompt enforcing citation by professor name and rating, a low-confidence warning when fewer than 3 chunks are retrieved, and `evaluate.py` that runs all 5 questions and prints results alongside expected answers for manual grading.
- *What I changed or overrode:* The original version used the Anthropic API. I directed Claude to switch to the Groq API with `llama-3.3-70b-versatile` since I had a free Groq API key. I also verified the system prompt rules matched what was described in `planning.md` and kept all 7 grounding rules intact.