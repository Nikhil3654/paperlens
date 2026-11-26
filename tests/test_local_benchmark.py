import json

from scripts.benchmark_local import run_benchmark


class ToyService:
    def ready(self):
        return True

    def search(self, question, search_mode="hybrid"):
        paper = "LoRA" if question == "good" else "BERT"
        evidence = [{"paper_title": paper, "page_number": 2, "chunk_id": "one"}]
        return {"evidence_used": evidence, "citations": [{"paper_title": paper, "page_number": 2, "chunk_id": "one"}],
                "confidence": "medium"}


def test_live_results_not_hardcoded(tmp_path):
    csv_file = tmp_path / "q.csv"
    csv_file.write_text("question,expected_paper,expected_pages\ngood,LoRA,2\nbad,LoRA,2\n")
    out = tmp_path / "report"
    summary = run_benchmark(ToyService(), csv_file, out)
    assert summary["hybrid"]["top1_paper_accuracy"] == 0.5
    assert summary["semantic"]["strict_paper_page_hit_at5"] == 0.5
    assert (out / "details.csv").exists()
    assert json.loads((out / "summary.json").read_text()) == summary
