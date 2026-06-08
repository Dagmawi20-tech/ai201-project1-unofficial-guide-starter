# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

**Student reviews of professors and courses at Minnesota State University, Mankato (MNSU)**

This knowledge is valuable because it captures what students actually experience — teaching quality, grading behavior, exam difficulty, and workload reality — none of which appears in official course catalogs or department websites. It is hard to find through official channels because it is scattered across Rate My Professors, Reddit threads, and student forums, written in inconsistent formats, and impossible to query in natural language. There is no single place where an MNSU student can ask "which CS professor actually explains things well?" and get a grounded, sourced answer.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate My Professors — John Burke | IT dept. Highly rated for practical, applied coding instruction. 10+ reviews. | https://www.ratemyprofessors.com/professor/2555592 / `docs/rmp_burke_john.txt` |
| 2 | Rate My Professors — Rebecca Bates | CS dept. Large, polarizing review set. Useful negative and positive signal. | https://www.ratemyprofessors.com/professor/625846 / `docs/rmp_bates_rebecca.txt` |
| 3 | Rate My Professors — Abo Habib | Accounting dept. 3.2/5, 156 ratings. One of the most-reviewed professors at MNSU. | https://www.ratemyprofessors.com/professor/361747 / `docs/rmp_habib_abo.txt` |
| 4 | Rate My Professors — Steven Smith | Theater dept. 4.7/5, 110 ratings, 100% would take again — most-reviewed at MNSU. | https://www.ratemyprofessors.com/search/professors/559?q=Steven+Smith / `docs/rmp_smith_steven.txt` |
| 5 | Rate My Professors — Scott Page | Education dept. 4.1/5, 36 ratings, 84% would take again. | https://www.ratemyprofessors.com/search/professors/559?q=Scott+Page / `docs/rmp_page_scott.txt` |
| 6 | Rate My Professors — Yea-Ling Tsao | Mathematics dept. 4.0/5, 31 ratings. | https://www.ratemyprofessors.com/search/professors/559?q=Yea-Ling+Tsao / `docs/rmp_tsao_yea_ling.txt` |
| 7 | Rate My Professors — Mark Hall | Marketing dept. 1.8/5, 74 ratings. Highly reviewed negative case — useful contrast. | https://www.ratemyprofessors.com/professor/501100 / `docs/rmp_hall_mark.txt` |
| 8 | Rate My Professors — In-Jae Kim | Mathematics dept. | https://www.ratemyprofessors.com/professor/926604 / `docs/rmp_kim_in_jae.txt` |
| 9 | Rate My Professors — MNSU school page | General student impressions of the university overall (academics, campus life, cost). | https://www.ratemyprofessors.com/school/559 / `docs/rmp_school_mnsu.txt` |
| 10 | RMP aggregator — ratemyprofessors.io | Cross-listed helpfulness, clarity, and ease scores for CS, Math, Engineering, Accounting profs. | https://ratemyprofessors.io/minnesota-state-university-mankato / `docs/aggregator_mnsu.txt` |
| 11 | r/MNSU — professor advice thread | Reddit thread with general professor recommendations and warnings from students. | https://www.reddit.com/r/MNSU/ / `docs/reddit_mnsu_professor_advice.txt` |
| 12 | r/MNSU — CS/IT courses thread | Reddit thread specifically about which CS/IT courses to take and which professors to avoid. | https://www.reddit.com/r/MNSU/ / `docs/reddit_mnsu_cs_courses.txt` |

> **Collection note:** RMP blocks automated scraping. All RMP documents are collected by manually copying review text into `.txt` files. Each review is formatted as `[X/5] review text here`, one review per paragraph, separated by blank lines.

---

## Chunking Strategy

**Chunk size:** One review = one chunk (~80–200 tokens for RMP reviews; ~100–300 tokens for Reddit comments). No fixed character limit — chunk boundaries follow natural review/comment boundaries.

**Overlap:** None for RMP reviews (each review is self-contained — overlapping would mix quotes from different students, making citation ambiguous). 30-token overlap for Reddit comments (comments sometimes reference prior ones; small overlap preserves cross-comment context).

**Reasoning:**
RMP reviews are short and self-contained — each one expresses a complete student opinion about a specific professor. Splitting a review mid-sentence would destroy its meaning. Merging multiple reviews into one chunk would make it impossible to attribute any claim to a specific student's experience or rating. The 1-review-1-chunk approach also makes metadata attachment clean: every chunk carries `professor_name`, `department`, `rating`, and `source_url` without ambiguity.

What bad chunking looks like:
- *Too small* (sentence-level): A chunk reading "She grades hard." has no professor name, no course context — the retriever can't know who "she" is.
- *Too large* (all reviews merged): A 2,000-token chunk about one professor would crowd out other relevant results and make specific citation impossible.

**Preprocessing before chunking:**
1. Strip any HTML or formatting artifacts from copied text.
2. Prepend each chunk with a context header: `[Professor: X | Dept: Y | Rating: Z/5]`
3. Filter Reddit comments under 80 characters (pure reactions, no signal).
4. Normalize all ratings to `X/5` format.

**Final chunk count:** ~120–150 chunks expected (8–15 reviews per professor × 8 professors, plus school reviews, aggregator rows, and Reddit comments).

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (local, no API key required). Chosen because it runs locally, is free, handles short opinionated text well, and has a 256-token max input that fits all chunks without truncation.

**Top-k:** 5 chunks per query.
- Too few (k=2): may miss relevant reviews if the embedding doesn't exactly match query phrasing.
- Too many (k=10+): floods the LLM with marginally relevant content, increasing hallucination risk.
- k=5 gives the model enough variety to synthesize across multiple student voices without overwhelming the context.

**Metadata filtering:** Queries mentioning a professor name pre-filter by `professor_name`. Queries mentioning a department pre-filter by `department`. This prevents a query about CS professors from retrieving Theater reviews that happen to use similar language.

**Production tradeoff reflection:**
If cost were no constraint, I would weigh three tradeoffs. First, `text-embedding-3-large` (OpenAI) offers higher accuracy on nuanced distinctions — e.g., "good at giving feedback" vs. "good at lecturing" — but costs per token and requires an API key. Second, `multilingual-e5-large` would better handle international student reviews that code-switch between English and another language, which is relevant at MNSU given its international student population. Third, higher-latency models are acceptable here since this is not real-time autocomplete — a 500ms retrieval delay is fine for a query interface.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about John Burke's teaching style? | Must reference Burke specifically, mention practical/applied coding instruction, cite at least one positive review. Must NOT reference any other professor. |
| 2 | Is Mark Hall a good professor? | Must reflect the low rating (1.8/5) and majority negative sentiment. A correct answer does NOT say he is good. Should cite specific student complaints. |
| 3 | Which math professor at MNSU has the best student ratings? | Must name Yea-Ling Tsao (4.0/5, 31 ratings) or In-Jae Kim based on retrieved data. Must not hallucinate a professor not in the corpus. |
| 4 | What do students say about difficulty in the CS department? | Must draw from Bates and/or Million reviews. Must cite specific difficulty observations (hard tests, heavy assignments) — not generic statements. |
| 5 | Who is the most beloved professor at MNSU according to student reviews? | Must name Steven Smith (4.7/5, 110 ratings, 100% would take again) and cite his rating and review count as evidence. A wrong answer names anyone else as #1. |

---

## Anticipated Challenges

1. **Off-topic retrieval from generic review language.** Reviews often use vague phrases like "great professor," "hard tests," or "lots of homework" that match many queries regardless of who they're about. Without metadata filtering, a query about math professors might retrieve Theater reviews that happen to mention difficulty. Mitigation: prepend every chunk with a professor/department context header, and apply department pre-filters where the query names a subject area.

2. **Thin corpus for less-reviewed professors.** Flint Million and In-Jae Kim have fewer reviews. A user asking specifically about them may get only 2–3 retrieved chunks — not enough to synthesize a confident answer. Mitigation: the generation prompt instructs the LLM to explicitly say "only a few reviews are available for this professor" when fewer than 3 chunks are retrieved, rather than overstating confidence.

3. **Inconsistent professor name formatting across sources.** RMP may list "J. Burke" while Reddit says "Professor Burke" or just "Burke." Metadata `professor_name` must be normalized at ingestion. A name normalization map (`burke`, `prof burke`, `john burke` → `John Burke`) is applied at query time.

4. **RMP corpus bias toward extreme opinions.** Students who feel strongly positive or negative are more likely to leave reviews. The corpus may not represent the median student experience. Mitigation: the generation system prompt notes this explicitly so the LLM can qualify its answers appropriately.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE OVERVIEW                            │
└─────────────────────────────────────────────────────────────────┘

  [1] Document Ingestion
      Tool: Python (manual .txt file collection)
      Input: /docs/*.txt  (RMP reviews, Reddit threads)
      Output: raw text strings + source metadata dicts

         │
         ▼

  [2] Chunking
      Tool: custom chunk_text() — Python
      Logic: split on blank lines (1 review = 1 chunk)
             prepend context header to each chunk
             filter Reddit comments < 80 chars
      Output: list of {text, metadata} dicts

         │
         ▼

  [3] Embedding
      Tool: sentence-transformers / all-MiniLM-L6-v2
      Input: chunk text strings
      Output: 384-dimensional float vectors

         │
         ▼

  [4] Vector Store
      Tool: ChromaDB (local, persistent)
      Stores: vectors + metadata
              (professor_name, department, rating,
               source_type, source_url)
      Supports: cosine similarity search + metadata filtering

         │
         ▼  ◄── user query (natural language)

  [5] Retrieval
      Logic: [optional metadata filter]
             → cosine similarity search
             → return top-5 chunks + metadata
      Tool: ChromaDB query API

         │
         ▼

  [6] Generation
      Tool: Claude API (claude-haiku-4-5)
      Input: system prompt + retrieved chunks as context
      Output: grounded answer with professor name + rating citations
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**
I will give Claude the Chunking Strategy section of this file plus a sample `.txt` file showing how my reviews are formatted (one review per paragraph, prefixed with `[X/5]`). I will ask it to implement a `chunk_text(filepath)` function that splits on blank lines, prepends the context header, filters short Reddit comments, and returns a list of `{text, metadata}` dicts. I will verify the output by running it on one of my real `.txt` files and checking that each returned chunk contains exactly one review with the correct metadata keys.

**Milestone 4 — Embedding and retrieval:**
I will give Claude the Retrieval Approach section plus the output schema from `chunk_text()`. I will ask it to implement `ingest.py` (reads all files from `/docs/`, calls `chunk_text()`, embeds with `all-MiniLM-L6-v2`, upserts into ChromaDB) and `retrieve(query, department=None, professor=None, k=5)` (applies optional metadata pre-filter, runs vector search, returns top-k chunks with metadata). I will verify by running a known query ("John Burke teaching style") and checking that all 5 returned chunks are from `rmp_burke_john.txt`.

**Milestone 5 — Generation and interface:**
I will give Claude the Evaluation Plan section (so it knows the expected answer shape) plus my 5 test questions. I will ask it to implement `generate(query, chunks)` — a function that formats retrieved chunks into a context block and calls the Claude API with a system prompt that enforces citation by professor name and rating, and flags low-confidence answers when fewer than 3 chunks are retrieved. I will verify by running all 5 evaluation questions and checking responses against the expected answers in the table above.