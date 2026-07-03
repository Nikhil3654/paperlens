let lastAnswer = null;

const statusEl = document.getElementById("status");
const paperListEl = document.getElementById("paperList");
const questionEl = document.getElementById("question");
const answerCard = document.getElementById("answerCard");
const answerText = document.getElementById("answerText");
const strengthBadge = document.getElementById("strengthBadge");
const citationsEl = document.getElementById("citations");
const evidenceEl = document.getElementById("evidence");

async function loadStatus() {
  const response = await fetch("/api/health");
  const data = await response.json();

  if (data.ready) {
    statusEl.textContent = `${data.paper_count} papers · ${data.chunk_count} chunks`;
  } else {
    statusEl.textContent = "Index not ready";
  }
}

async function loadPapers() {
  const response = await fetch("/api/papers");
  const data = await response.json();

  paperListEl.innerHTML = "";

  data.papers.forEach((paper) => {
    const label = document.createElement("label");
    label.className = "paper-item";
    label.innerHTML = `<input type="checkbox" checked value="${paper}" /> <span>${paper}</span>`;
    paperListEl.appendChild(label);
  });
}

function selectedPapers() {
  return Array.from(paperListEl.querySelectorAll("input:checked")).map((input) => input.value);
}

function searchMode() {
  return document.querySelector("input[name='searchMode']:checked").value;
}

async function search() {
  const question = questionEl.value.trim();

  if (!question) {
    return;
  }

  statusEl.textContent = "Searching...";

  const response = await fetch("/api/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      paper_titles: selectedPapers(),
      search_mode: searchMode(),
    }),
  });

  const data = await response.json();
  lastAnswer = data;
  renderAnswer(data);
  await loadStatus();
}

function renderAnswer(data) {
  answerCard.classList.remove("hidden");
  answerText.textContent = data.answer;
  strengthBadge.textContent = `Evidence: ${data.evidence_strength}`;

  citationsEl.innerHTML = "";
  data.citations.forEach((citation) => {
    const card = document.createElement("div");
    card.className = "citation-card";
    card.textContent = citation.citation;
    citationsEl.appendChild(card);
  });

  evidenceEl.innerHTML = "";
  data.evidence.forEach((chunk, index) => {
    const card = document.createElement("div");
    card.className = "evidence-card";
    card.innerHTML = `
      <strong>${index + 1}. ${chunk.paper_title}, page ${chunk.page_number}</strong>
      <p>${chunk.text}</p>
      <small>
        Search: ${(chunk.search_score || 0).toFixed(3)}
        ${chunk.keyword_score !== null && chunk.keyword_score !== undefined ? ` · Keyword: ${chunk.keyword_score.toFixed(3)}` : ""}
        ${chunk.rrf_score !== null && chunk.rrf_score !== undefined ? ` · RRF: ${chunk.rrf_score.toFixed(4)}` : ""}
        ${chunk.rerank_score !== null && chunk.rerank_score !== undefined ? ` · Rerank: ${chunk.rerank_score.toFixed(3)}` : ""}
      </small>
    `;
    evidenceEl.appendChild(card);
  });
}

document.getElementById("searchButton").addEventListener("click", search);

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionEl.value = button.dataset.question;
  });
});

document.getElementById("downloadButton").addEventListener("click", () => {
  if (!lastAnswer) return;

  const text = [
    `Question: ${lastAnswer.question}`,
    "",
    "Answer:",
    lastAnswer.answer,
    "",
    "Citations:",
    ...lastAnswer.citations.map((citation) => `- ${citation.citation}`),
  ].join("\n");

  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = "paperlens-answer.txt";
  link.click();

  URL.revokeObjectURL(url);
});

loadStatus();
loadPapers();