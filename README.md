---
title: PaperLens
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.36.0"
python_version: "3.10"
app_file: app.py
pinned: false
---

# PaperLens

PaperLens is a citation-grounded research assistant that answers questions from research papers using retrieval, reranking, and source-backed evidence.

The project is built to show a practical RAG workflow, not just a PDF chatbot. It focuses on transparent retrieval, page-level citations, evidence strength, and measurable retrieval quality.

## Live Demo

Hugging Face Space:

https://huggingface.co/spaces/sc-ss/paperlens

## What PaperLens Does

- Reads research papers from PDF files
- Supports the built-in sample paper collection
- Supports user-uploaded PDFs
- Splits papers into page-aware searchable chunks
- Builds semantic search with Sentence Transformers and FAISS
- Adds BM25 keyword search for hybrid retrieval
- Reranks evidence with a cross-encoder
- Produces citation-grounded answers from retrieved evidence
- Shows citations, page numbers, evidence chunks, and relevance scores
- Warns when uploaded PDFs may have poor text extraction
- Includes benchmark results for retrieval quality

## Paper Collection

The default demo uses five public AI research papers:

- Attention Is All You Need
- BERT
- Retrieval-Augmented Generation
- LoRA
- Chain-of-Thought Prompting

The app can also index user-uploaded PDFs during a session.

## Architecture

```text
PDFs
  -> page-level text extraction
  -> page-aware chunks
  -> Sentence Transformer embeddings
  -> FAISS semantic search
  -> BM25 keyword search
  -> hybrid retrieval
  -> cross-encoder reranking
  -> citation-grounded answer
```

## Retrieval Modes

PaperLens supports two retrieval modes:

| Mode | Description |
|---|---|
| Semantic search | Uses dense embeddings and FAISS to find meaning-based matches |
| Hybrid search | Combines FAISS semantic search with BM25 keyword search before reranking |

Hybrid search is useful for technical papers because it can preserve exact terms, acronyms, and method names while still finding semantically related evidence.

## Evaluation

PaperLens was evaluated on 15 manually written questions across five AI research papers.

| Metric | Result |
|---|---:|
| Top-1 paper routing accuracy | 100% |
| Top-5 paper routing accuracy | 100% |
| Strict page-level citation hit rate | 86.7% |

The strict page-level citation metric checks whether retrieved evidence appears on the expected source page. This is intentionally harder than just finding the correct paper.

## Example Questions

- What is self-attention and why is it useful?
- What is masked language modeling in BERT?
- How does retrieval augmented generation use external knowledge?
- How does LoRA reduce the number of trainable parameters?
- Why does chain-of-thought prompting improve reasoning?

## Project Structure

```text
paperlens/
  app/
    streamlit_app.py
  src/
    pdf_reader.py
    text_chunks.py
    search_index.py
    hybrid_search.py
    reranker.py
    answer_writer.py
    evaluation.py
  data/
    papers/
    questions/
  artifacts/
  assets/
    screenshots/
    diagrams/
  requirements.txt
  app.py
  README.md
```

## Tech Stack

- Python
- Streamlit
- Hugging Face Spaces
- pypdf
- Sentence Transformers
- FAISS
- BM25
- Cross-encoder reranking
- Pandas
- NumPy

## Why This Project Matters

PaperLens demonstrates an end-to-end RAG system with real engineering decisions:

- PDF ingestion with page metadata
- Chunking strategy for citation reliability
- Semantic retrieval using embeddings
- Keyword retrieval using BM25
- Hybrid retrieval for stronger evidence selection
- Cross-encoder reranking
- Evidence-based answer generation
- Manual retrieval evaluation

## Limitations

- Scanned or image-based PDFs may need OCR.
- Free CPU deployment can be slower on first startup.
- Uploaded PDFs are indexed during the current app session.
- Page-level evaluation is strict, so useful evidence may sometimes appear on a nearby page.
- The default answer writer is extractive and does not require a paid LLM API.

## Future Improvements

- Add OCR support for scanned PDFs
- Save and load prebuilt search artifacts for faster startup
- Expand the benchmark from 15 to 30 questions
- Add side-by-side semantic vs hybrid retrieval evaluation
- Add downloadable answer reports
- Add optional user-provided LLM key support while keeping the free no-key mode


