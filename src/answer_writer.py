from typing import Dict, List


MIN_RERANK_SCORE = 1.0


def format_citation(chunk: Dict) -> str:
    """Create a readable citation label for a retrieved chunk."""
    return f"{chunk['paper_title']}, page {chunk['page_number']}"


def has_enough_evidence(chunks: List[Dict], min_score: float = MIN_RERANK_SCORE) -> bool:
    """Decide whether retrieved evidence is strong enough to answer."""
    if not chunks:
        return False

    best_score = chunks[0].get("rerank_score", chunks[0].get("search_score", 0.0))
    return best_score >= min_score


def write_evidence_summary(chunks: List[Dict], max_chunks: int = 3) -> str:
    """
    Create a simple grounded answer from retrieved evidence.

    This is intentionally extractive for the first version. It avoids pretending
    to know more than the retrieved paper text supports.
    """
    selected_chunks = chunks[:max_chunks]

    summary_parts = []

    for chunk in selected_chunks:
        citation = format_citation(chunk)
        text = chunk["text"].strip()

        if len(text) > 700:
            text = text[:700].rsplit(" ", 1)[0] + "..."

        summary_parts.append(f"According to {citation}, {text}")

    return "\n\n".join(summary_parts)


def answer_from_evidence(
    query: str,
    chunks: List[Dict],
    min_score: float = MIN_RERANK_SCORE,
    max_chunks: int = 3,
) -> Dict:
    """
    Produce a citation-grounded answer from retrieved and reranked chunks.
    """
    if not has_enough_evidence(chunks, min_score=min_score):
        return {
            "query": query,
            "answer": (
                "I do not have enough strong evidence from the selected papers "
                "to answer this question reliably."
            ),
            "citations": [],
            "evidence_used": [],
            "confidence": "low",
        }

    selected_chunks = chunks[:max_chunks]

    citations = []
    for chunk in selected_chunks:
        citation = {
            "paper_title": chunk["paper_title"],
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"],
            "citation": format_citation(chunk),
        }
        citations.append(citation)

    return {
        "query": query,
        "answer": write_evidence_summary(selected_chunks, max_chunks=max_chunks),
        "citations": citations,
        "evidence_used": selected_chunks,
        "confidence": "medium",
    }

def format_answer_for_display(answer: Dict) -> str:
    """Format a grounded answer for notebook or app display."""
    lines = []

    lines.append("Answer")
    lines.append(answer["answer"])

    if answer["citations"]:
        lines.append("")
        lines.append("Citations")

        seen = set()
        for citation in answer["citations"]:
            citation_text = citation["citation"]

            if citation_text in seen:
                continue

            seen.add(citation_text)
            lines.append(f"- {citation_text}")

    lines.append("")
    lines.append(f"Confidence: {answer['confidence']}")

    return "\n".join(lines)