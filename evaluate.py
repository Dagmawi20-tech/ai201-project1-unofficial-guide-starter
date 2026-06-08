"""
evaluate.py — The Unofficial Guide to MNSU Professors
Runs all 5 evaluation questions from planning.md and prints results
side-by-side with expected answers for manual grading.

Usage:
    python evaluate.py
"""

from generate import generate, print_result

EVAL_QUESTIONS = [
    {
        "id": 1,
        "question": "What do students say about John Burke's teaching style?",
        "professor": "John Burke",
        "department": None,
        "expected": (
            "Must reference Burke specifically, mention practical/applied coding "
            "instruction, cite at least one positive review. Must NOT reference any "
            "other professor."
        ),
    },
    {
        "id": 2,
        "question": "Is Mark Hall a good professor?",
        "professor": "Mark Hall",
        "department": None,
        "expected": (
            "Must reflect low rating (1.8/5) and majority negative sentiment. "
            "A correct answer does NOT say he is good. Should cite specific complaints."
        ),
    },
    {
        "id": 3,
        "question": "Which math professor at MNSU has the best student ratings?",
        "professor": None,
        "department": "Mathematics",
        "expected": (
            "Must name Marino Romero (4.3/5, 86% would take again) or In-Jae Kim. "
            "Must not hallucinate a professor not in the corpus."
        ),
    },
    {
        "id": 4,
        "question": "What do students say about Abo Habib's exams?",
        "professor": "Abo Habib",
        "department": None,
        "expected": (
            "Must draw from Habib reviews. Must cite specific observations about "
            "exam difficulty and grading — not generic statements."
        ),
    },
    {
        "id": 5,
        "question": "Who is the most beloved professor at MNSU according to student reviews?",
        "professor": None,
        "department": None,
        "expected": (
            "Must name Steven Smith (4.7/5, 110 ratings, 100% would take again) "
            "and cite his rating and review count. Wrong answer names anyone else as #1."
        ),
    },
]


def run_evaluation():
    print("=" * 60)
    print("  EVALUATION REPORT — The Unofficial Guide to MNSU")
    print("=" * 60)
    print()

    for eq in EVAL_QUESTIONS:
        print(f"{'=' * 60}")
        print(f"Question {eq['id']}: {eq['question']}")
        print(f"Expected: {eq['expected']}")
        print(f"{'─' * 60}")

        result = generate(
            eq["question"],
            professor=eq["professor"],
            department=eq["department"],
        )
        print_result(result)

        # Manual grading prompts
        print()
        print("Retrieval quality  → [ Relevant / Partially relevant / Off-target ]")
        print("Response accuracy  → [ Accurate / Partially accurate / Inaccurate ]")
        print()


if __name__ == "__main__":
    run_evaluation()
