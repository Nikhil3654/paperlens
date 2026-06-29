from typing import Dict, List

import numpy as np
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> List[str]:
    """Tokenize text for BM25 keyword search."""
    return text.lower().split()


def build_bm25_index(chunks: List[Dict]) -> BM25Okapi:
    """Build a BM25 index over chunk text."""
    tokenized_chunks = [tokenize(chunk["text"]) for chunk in chunks]
    return BM25Okapi(tokenized_chunks)


def min_max_normalize(scores: List[float]) -> List[float]:
    """Normalize scores to the 0-1 range."""
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [0.0 for _ in scores]

    return [(score - min_score) / (max_score - min_score) for score in scores]


def hybrid_search_chunks(
    query: str,
    chunks: List[Dict],
    semantic_model,
    semantic_index,
    bm25_index: BM25Okapi,
    top_k: int = 10,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> List[Dict]:
    """
    Search chunks using a weighted blend of semantic search and BM25 keyword search.
    """
    from src.search_index import search_chunks

    semantic_results = search_chunks(
        query=query,
        chunks=chunks,
        model=semantic_model,
        index=semantic_index,
        top_k=min(top_k * 3, len(chunks)),
    )

    semantic_by_id = {
        result["chunk_id"]: result for result in semantic_results
    }

    tokenized_query = tokenize(query)
    bm25_scores = bm25_index.get_scores(tokenized_query)

    top_bm25_indices = np.argsort(bm25_scores)[::-1][: min(top_k * 3, len(chunks))]

    candidate_ids = set(semantic_by_id.keys())

    for index in top_bm25_indices:
        candidate_ids.add(chunks[index]["chunk_id"])

    candidates = []

    semantic_scores = []
    keyword_scores = []

    for chunk_id in candidate_ids:
        chunk_index = next(
            index for index, chunk in enumerate(chunks) if chunk["chunk_id"] == chunk_id
        )

        chunk = dict(chunks[chunk_index])

        semantic_score = semantic_by_id.get(chunk_id, {}).get("search_score", 0.0)
        keyword_score = float(bm25_scores[chunk_index])

        candidates.append(chunk)
        semantic_scores.append(semantic_score)
        keyword_scores.append(keyword_score)

    normalized_semantic = min_max_normalize(semantic_scores)
    normalized_keyword = min_max_normalize(keyword_scores)

    scored_candidates = []

    for chunk, semantic_score, keyword_score, norm_semantic, norm_keyword in zip(
        candidates,
        semantic_scores,
        keyword_scores,
        normalized_semantic,
        normalized_keyword,
    ):
        hybrid_score = (
            semantic_weight * norm_semantic
            + keyword_weight * norm_keyword
        )

        chunk["search_score"] = float(semantic_score)
        chunk["keyword_score"] = float(keyword_score)
        chunk["hybrid_score"] = float(hybrid_score)

        scored_candidates.append(chunk)

    scored_candidates.sort(key=lambda item: item["hybrid_score"], reverse=True)

    return scored_candidates[:top_k]