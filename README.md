---
title: PaperLens
emoji: 📄
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

The goal is to build a practical RAG system that does more than chat with PDFs. PaperLens focuses on transparent retrieval, reliable citations, and measurable answer quality.

## What It Does

- Reads research papers from PDF files
- Splits papers into searchable text chunks with page metadata
- Builds a vector search index over the paper collection
- Reranks retrieved evidence before answering
- Produces answers with citations from the source papers
- Falls back when there is not enough evidence
- Measures retrieval and answer quality using a small evaluation set

## Project Workflow

This project uses a remote-first workflow:

- Kaggle notebooks for experiments and heavier processing
- GitHub for source code, documentation, and project history
- Hugging Face Spaces for the deployed demo
- Local machine for light editing and commits

## Planned Papers

The first version will use five public AI research papers:

- Attention Is All You Need
- BERT
- Retrieval-Augmented Generation
- LoRA
- Chain-of-Thought Prompting

## Project Structure

`	ext
paperlens/
  app/
  src/
  notebooks/
  data/
  artifacts/
  assets/
`
## Learning Goals
Understand the full RAG pipeline
Compare chunking strategies
Build vector search with FAISS
Add reranking for stronger retrieval
Design citation-grounded answer generation
Evaluate retrieval quality instead of relying only on demos
Status
In progress.
=======
---
title: Paperlens
emoji: 🚀
colorFrom: red
colorTo: red
sdk: docker
app_port: 8501
tags:
- streamlit
pinned: false
short_description: Streamlit template space
---

# Welcome to Streamlit!

Edit `/src/streamlit_app.py` to customize this app to your heart's desire. :heart:

If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).