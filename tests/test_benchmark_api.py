"""Offline regression tests for the PaperLens benchmark scorer."""
import unittest

from scripts.benchmark_api import parse_pages, score_response, summarise


class BenchmarkScorerTests(unittest.TestCase):
    def test_parse_pages(self):
        self.assertEqual(parse_pages("2, 4, 7"), {2, 4, 7})
        self.assertEqual(parse_pages(""), set())

    def test_wrong_paper_same_page_not_a_page_hit(self):
        question = {"question": "What is LoRA?", "expected_paper": "LoRA", "expected_pages": "3"}
        response = {"evidence_used": [
            {"paper_title": "BERT", "page_number": 3, "chunk_id": "other"},
            {"paper_title": "LoRA", "page_number": 8, "chunk_id": "lora8"},
        ], "citations": [], "confidence": "medium"}
        scored = score_response(question, response)
        self.assertTrue(scored["top5_paper_hit"])
        self.assertFalse(scored["strict_paper_page_hit_at5"])
        self.assertEqual(scored["reciprocal_rank_at5"], 0.5)

    def test_matching_paper_and_page_is_hit(self):
        question = {"question": "What is LoRA?", "expected_paper": "LoRA", "expected_pages": "3, 4"}
        response = {"evidence_used": [
            {"paper_title": "LoRA", "page_number": 4, "chunk_id": "lora4"},
        ], "citations": [{"paper_title": "LoRA", "page_number": 4, "chunk_id": "lora4"}],
           "confidence": "medium"}
        scored = score_response(question, response)
        self.assertTrue(scored["top1_paper_hit"])
        self.assertTrue(scored["strict_paper_page_hit_at5"])
        self.assertTrue(scored["citation_mapping_valid"])

    def test_missing_page_label_is_excluded_not_failure(self):
        question = {"question": "Test", "expected_paper": "BERT", "expected_pages": ""}
        scored = score_response(question, {"evidence_used": [], "citations": [], "confidence": "low"})
        self.assertIsNone(scored["strict_paper_page_hit_at5"])

    def test_unanswerable_abstention(self):
        question = {"question": "Invented query", "expected_paper": "None", "answerable": "false"}
        scored = score_response(question, {"evidence_used": [], "citations": [], "confidence": "low"})
        self.assertTrue(scored["correct_abstention"])

    def test_invalid_citation_reference(self):
        question = {"question": "Test", "expected_paper": "BERT"}
        scored = score_response(question, {"evidence_used": [
            {"paper_title": "BERT", "page_number": 1, "chunk_id": "a"}],
            "citations": [{"paper_title": "BERT", "page_number": 2, "chunk_id": "b"}]})
        self.assertFalse(scored["citation_mapping_valid"])

    def test_summary_keeps_errors_separate(self):
        rows = [
            {"mode": "semantic", "top1_paper_hit": True, "latency_ms": 100},
            {"mode": "semantic", "error": "timeout"},
        ]
        s = summarise(rows, ["semantic"])["semantic"]
        self.assertEqual(s["failed_queries"], 1)
        self.assertEqual(s["top1_paper_accuracy"], 1.0)
        self.assertEqual(s["latency_p50_ms"], 100.0)


if __name__ == "__main__":
    unittest.main()
