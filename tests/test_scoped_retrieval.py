"""Regression tests for scoped FAISS/BM25 alignment (no model download)."""
import importlib.util
import sys
import types
from unittest.mock import patch

import numpy as np
import pytest


# Create lightweight import shims only on machines without ML dependencies.
# In Kaggle the real installed libraries are imported instead.
for module_name, attrs in {
    "faiss": {"Index": object},
    "rank_bm25": {"BM25Okapi": object},
    "sentence_transformers": {"SentenceTransformer": object, "CrossEncoder": object},
}.items():
    if importlib.util.find_spec(module_name) is None:
        stub = types.ModuleType(module_name)
        for key, value in attrs.items():
            setattr(stub, key, value)
        sys.modules[module_name] = stub

from api.paper_service import PaperLensService
from src.evaluation import evaluate_retrieval
from src.hybrid_search import rrf_hybrid_search_chunks
from src.search_index import search_chunks
import pandas as pd


class FakeIndex:
    def __init__(self, emb):
        self.embeddings = np.array(emb)
        self.ntotal = len(emb)


class FakeBM25:
    def __init__(self, chunks):
        self.doc_len = [len(c["text"].split()) for c in chunks]


def make_service():
    service = PaperLensService()
    chunks = [
        {"paper_title": "BERT", "page_number": 1, "text": "BERT abstract", "chunk_id": "b1"},
        {"paper_title": "LoRA", "page_number": 3, "text": "LoRA weights", "chunk_id": "l1"},
        {"paper_title": "BERT", "page_number": 2, "text": "BERT masks", "chunk_id": "b2"},
        {"paper_title": "LoRA", "page_number": 4, "text": "Low rank", "chunk_id": "l2"},
    ]
    matrix = np.array([[1, 0], [0, 1], [2, 0], [0, 2]], dtype="float32")
    service.state = {"chunks": chunks, "embeddings": matrix, "index": FakeIndex(matrix),
                     "bm25_index": FakeBM25(chunks), "embedding_model": object(),
                     "reranker": object(), "paper_count": 2, "page_count": 4,
                     "chunk_count": 4}
    return service


def test_subset_indexes_are_built_over_the_same_chunk_order():
    service = make_service()
    with patch("api.paper_service.build_search_index", side_effect=FakeIndex), \
         patch("api.paper_service.build_bm25_index", side_effect=FakeBM25):
        chunks, index, bm25 = service._retrieval_scope(["LoRA"])
        assert [c["chunk_id"] for c in chunks] == ["l1", "l2"]
        assert index.embeddings.tolist() == [[0.0, 1.0], [0.0, 2.0]]
        assert len(bm25.doc_len) == len(chunks) == index.ntotal == 2
        assert service._retrieval_scope(["LoRA"])[1] is index


def test_unknown_or_empty_paper_selection_is_rejected():
    service = make_service()
    with pytest.raises(ValueError, match="Unknown paper"):
        service._retrieval_scope(["Unlisted Paper"])
    with pytest.raises(ValueError, match="at least one"):
        service._retrieval_scope([])


def test_selected_paper_search_never_returns_a_different_paper():
    service = make_service()
    def fake_search(query, chunks, model, index, top_k):
        assert index.ntotal == len(chunks)
        return [{**c, "rerank_score": 3.0} for c in chunks]
    def fake_hybrid(query, chunks, semantic_model, semantic_index, bm25_index, top_k):
        assert semantic_index.ntotal == len(bm25_index.doc_len) == len(chunks)
        return [{**c, "rerank_score": 3.0} for c in chunks]
    with patch("api.paper_service.build_search_index", side_effect=FakeIndex), \
         patch("api.paper_service.build_bm25_index", side_effect=FakeBM25), \
         patch("api.paper_service.search_chunks", side_effect=fake_search), \
         patch("api.paper_service.rrf_hybrid_search_chunks", side_effect=fake_hybrid), \
         patch("api.paper_service.rerank_chunks", side_effect=lambda query, chunks, reranker, top_k: chunks[:top_k]):
        for mode in ["semantic", "hybrid"]:
            res = service.search("What is LoRA?", paper_titles=["LoRA"], search_mode=mode)
            assert res["evidence_used"]
            assert all(c["paper_title"] == "LoRA" for c in res["evidence_used"])


def test_search_refuses_misaligned_faiss_index():
    with pytest.raises(ValueError, match="misaligned"):
        search_chunks("query", [{"text": "a"}], model=object(), index=FakeIndex(np.ones((2, 2))), top_k=1)


def test_hybrid_refuses_misaligned_bm25_index():
    with pytest.raises(ValueError, match="misaligned"):
        rrf_hybrid_search_chunks("query", [{"text": "a"}], semantic_model=object(),
                                 semantic_index=FakeIndex(np.ones((1, 2))),
                                 bm25_index=FakeBM25([]), top_k=1)


def test_full_hit_requires_expected_paper_and_page_in_same_result():
    q = pd.DataFrame([{"question": "q", "expected_paper": "LoRA", "expected_pages": "3"}])
    result = evaluate_retrieval(
        questions=q, chunks=[], search_model=None, search_index=None,
        search_fn=lambda **_: [
            {"paper_title": "BERT", "page_number": 3, "chunk_id": "b3"},
            {"paper_title": "LoRA", "page_number": 4, "chunk_id": "l4"},
        ],
    )
    assert bool(result.iloc[0]["paper_hit"])
    assert bool(result.iloc[0]["page_hit"])
    assert not bool(result.iloc[0]["full_hit"])
