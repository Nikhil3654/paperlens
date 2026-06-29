from typing import Dict, List

import pandas as pd


def parse_expected_pages(value: str) -> List[int]:
    """Parse expected page numbers from a comma-separated string."""
    if pd.isna(value):
        return []

    return [int(page.strip()) for page in str(value).split(",") if page.strip()]


def page_hit(results: List[Dict], expected_pages: List[int]) -> bool:
    """Check whether any retrieved result comes from an expected page."""
    retrieved_pages = {result["page_number"] for result in results}
    return any(page in retrieved_pages for page in expected_pages)


def evaluate_retrieval(
    questions: pd.DataFrame,
    chunks: List[Dict],
    search_model,
    search_index,
    search_fn,
    reranker=None,
    rerank_fn=None,
    retrieve_k: int = 10,
    final_k: int = 5,
) -> pd.DataFrame:
    """
    Evaluate whether retrieval finds expected source pages.

    If reranker and rerank_fn are provided, evaluation uses reranked results.
    Otherwise it uses the raw search results.
    """
    rows = []

    for _, row in questions.iterrows():
        question = row["question"]
        expected_pages = parse_expected_pages(row["expected_pages"])

        retrieved = search_fn(
            query=question,
            chunks=chunks,
            model=search_model,
            index=search_index,
            top_k=retrieve_k,
        )

        if reranker is not None and rerank_fn is not None:
            final_results = rerank_fn(
                query=question,
                chunks=retrieved,
                reranker=reranker,
                top_k=final_k,
            )
        else:
            final_results = retrieved[:final_k]

        hit = page_hit(final_results, expected_pages)

        best_result = final_results[0] if final_results else {}

        rows.append(
            {
                "question": question,
                "expected_pages": expected_pages,
                "top_k_hit": hit,
                "best_page": best_result.get("page_number"),
                "best_chunk_id": best_result.get("chunk_id"),
                "best_search_score": best_result.get("search_score"),
                "best_rerank_score": best_result.get("rerank_score"),
                "retrieved_pages": [
                    result["page_number"] for result in final_results
                ],
                "notes": row.get("notes", ""),
            }
        )

    return pd.DataFrame(rows)


def summarize_retrieval_results(results: pd.DataFrame) -> Dict:
    """Create a small summary of retrieval evaluation results."""
    total_questions = len(results)

    if total_questions == 0:
        return {
            "total_questions": 0,
            "top_k_hits": 0,
            "top_k_hit_rate": 0.0,
        }

    top_k_hits = int(results["top_k_hit"].sum())

    return {
        "total_questions": total_questions,
        "top_k_hits": top_k_hits,
        "top_k_hit_rate": top_k_hits / total_questions,
    }