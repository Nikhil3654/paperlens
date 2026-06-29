from pathlib import Path
from urllib.request import urlretrieve

import streamlit as st

from src.answer_writer import answer_from_evidence
from src.pdf_reader import read_many_pdfs
from src.reranker import load_reranker, rerank_chunks
from src.search_index import build_search_index, embed_texts, load_embedding_model, search_chunks
from src.text_chunks import make_text_chunks


PAPERS = [
    {
        "title": "Attention Is All You Need",
        "file": "attention_is_all_you_need.pdf",
        "url": "https://arxiv.org/pdf/1706.03762",
    },
    {
        "title": "BERT",
        "file": "bert.pdf",
        "url": "https://arxiv.org/pdf/1810.04805",
    },
    {
        "title": "Retrieval-Augmented Generation",
        "file": "retrieval_augmented_generation.pdf",
        "url": "https://arxiv.org/pdf/2005.11401",
    },
    {
        "title": "LoRA",
        "file": "lora.pdf",
        "url": "https://arxiv.org/pdf/2106.09685",
    },
    {
        "title": "Chain-of-Thought Prompting",
        "file": "chain_of_thought_prompting.pdf",
        "url": "https://arxiv.org/pdf/2201.11903",
    },
]


SAMPLE_QUESTIONS = [
    "What is self-attention and why is it useful?",
    "What is masked language modeling in BERT?",
    "How does retrieval augmented generation use external knowledge?",
    "How does LoRA reduce the number of trainable parameters?",
    "Why does chain-of-thought prompting improve reasoning?",
]


def ensure_sample_papers() -> None:
    """Download sample papers if they are not already available."""
    paper_dir = Path("data/papers")
    paper_dir.mkdir(parents=True, exist_ok=True)

    for paper in PAPERS:
        path = paper_dir / paper["file"]

        if path.exists():
            continue

        urlretrieve(paper["url"], path)


@st.cache_resource(show_spinner="Preparing the research index...")
def build_paperlens_index():
    ensure_sample_papers()

    paper_inputs = []

    for paper in PAPERS:
        path = Path("data/papers") / paper["file"]

        if path.exists():
            paper_inputs.append(
                {
                    "path": str(path),
                    "title": paper["title"],
                }
            )

    if not paper_inputs:
        return None

    pages = read_many_pdfs(paper_inputs)
    chunks = make_text_chunks(pages=pages, chunk_size=220, overlap=40)

    embedding_model = load_embedding_model()
    embeddings = embed_texts([chunk["text"] for chunk in chunks], model=embedding_model)
    index = build_search_index(embeddings)

    reranker = load_reranker()

    return {
        "chunks": chunks,
        "embedding_model": embedding_model,
        "index": index,
        "reranker": reranker,
        "paper_count": len(paper_inputs),
        "chunk_count": len(chunks),
    }


st.set_page_config(
    page_title="PaperLens",
    page_icon="📄",
    layout="wide",
)

st.title("PaperLens")
st.caption("Ask research papers. Get cited answers.")

with st.sidebar:
    st.header("Paper Collection")
    for paper in PAPERS:
        st.write(f"- {paper['title']}")

    st.divider()
    st.write("Retrieval: FAISS + Sentence Transformers")
    st.write("Reranking: Cross-Encoder")
    st.write("Benchmark: 15 questions across 5 papers")

state = build_paperlens_index()

if state is None:
    st.warning("PaperLens could not prepare the sample paper collection.")
    st.stop()

st.info(
    f"Indexed {state['paper_count']} papers into {state['chunk_count']} searchable chunks."
)

selected_question = st.selectbox(
    "Try a sample question",
    SAMPLE_QUESTIONS,
)

custom_question = st.text_input(
    "Or ask your own question",
    placeholder="Ask about one of the papers...",
)

query = custom_question.strip() or selected_question

if st.button("Search Papers", type="primary"):
    retrieved = search_chunks(
        query=query,
        chunks=state["chunks"],
        model=state["embedding_model"],
        index=state["index"],
        top_k=10,
    )

    reranked = rerank_chunks(
        query=query,
        chunks=retrieved,
        reranker=state["reranker"],
        top_k=5,
    )

    answer = answer_from_evidence(
        query=query,
        chunks=reranked,
        min_score=1.0,
        max_chunks=3,
    )

    st.subheader("Answer")
    st.write(answer["answer"])

    st.subheader("Citations")
    if answer["citations"]:
        for citation in answer["citations"]:
            st.write(f"- {citation['citation']}")
    else:
        st.write("No strong citations found.")

    st.subheader("Evidence")
    for rank, chunk in enumerate(reranked, start=1):
        with st.expander(
            f"{rank}. {chunk['paper_title']} · page {chunk['page_number']}"
        ):
            st.write(f"Search score: {chunk.get('search_score', 0):.3f}")
            st.write(f"Rerank score: {chunk.get('rerank_score', 0):.3f}")
            st.write(chunk["text"])