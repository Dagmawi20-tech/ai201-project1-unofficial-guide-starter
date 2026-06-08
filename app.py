"""
app.py — The Unofficial Guide to MNSU Professors
Gradio web interface for querying the RAG system.

Usage:
    python app.py
    Open http://localhost:7860
"""

import gradio as gr
from generate import generate


def handle_query(question: str):
    """Run the full RAG pipeline and return answer + sources."""
    if not question.strip():
        return "Please enter a question.", ""

    result = generate(question)

    # Format sources
    source_files = list(set(c["source_file"] for c in result["chunks"]))
    sources = "\n".join(f"• {s}.txt" for s in sorted(source_files))

    # Append low-confidence warning to answer if triggered
    answer = result["answer"]
    if result["warned"]:
        answer += f"\n\n⚠ Only {len(result['chunks'])} source(s) retrieved — answer may be limited."

    return answer, sources


# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="The Unofficial Guide to MNSU Professors") as demo:
    gr.Markdown(
        """
        # 📚 The Unofficial Guide to MNSU Professors
        Ask questions about professors at Minnesota State University, Mankato.
        Answers are grounded in real student reviews from Rate My Professors.
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            inp = gr.Textbox(
                label="Your question",
                placeholder='e.g. "Is John Burke good for learning to code?" or "What do students say about Abo Habib\'s exams?"',
                lines=2,
            )
            btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        with gr.Column(scale=2):
            answer = gr.Textbox(label="Answer", lines=8, interactive=False)
        with gr.Column(scale=1):
            sources = gr.Textbox(label="Retrieved from", lines=8, interactive=False)

    gr.Markdown(
        """
        ---
        **Example questions to try:**
        - What do students say about John Burke's teaching style?
        - Is Mark Hall a good professor?
        - Which math professor at MNSU has the best student ratings?
        - What do students say about Abo Habib's exams?
        - Who is the most beloved professor at MNSU?
        """
    )

    # Wire up button and enter key
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
