let lastAnswer = null;

const statusEl = document.getElementById("status");
const statusDot = document.getElementById("statusDot");
const paperListEl = document.getElementById("paperList");
const questionEl = document.getElementById("question");
const answerCard = document.getElementById("answerCard");
const loadingCard = document.getElementById("loadingCard");
const answerText = document.getElementById("answerText");
const strengthBadge = document.getElementById("strengthBadge");
const citationsEl = document.getElementById("citations");
const evidenceEl = document.getElementById("evidence");
const searchButton = document.getElementById("searchButton");

async function loadStatus() {
  const response = await fetch("/api/health");
  const data = await response.json();

  if (data.ready) {
    statusEl.textContent = `${data.paper_count} papers · ${data.chunk_count} chunks`;
    statusDot.classList.add("ready");
  } else {
    statusEl.textContent = "Index not ready";
    statusDot.classList.remove("ready");
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

function setLoading(isLoading) {
  searchButton.disabled = isLoading;
  searchButton.textContent = isLoading ? "Searching..." : "Search Papers";

  if (isLoading) {
    loadingCard.classList.remove("hidden");
    answerCard.classList.add("hidden");
    statusEl.textContent = "Searching...";
    statusDot.classList.remove("ready");
  } else {
    loadingCard.classList.add("hidden");
  }
}

async function search() {
  const question = questionEl.value.trim();

  if (!question) {
    questionEl.focus();
    return;
  }

  setLoading(true);

  try {
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
  } catch (error) {
    answerCard.classList.remove("hidden");
    answerText.textContent = "Something went wrong while searching. Please try again.";
    citationsEl.innerHTML = "";
    evidenceEl.innerHTML = "";
  } finally {
    setLoading(false);
    await loadStatus();
  }
}

function badgeClass(strength) {
  if (strength === "weak") return "badge weak";
  if (strength === "moderate") return "badge moderate";
  return "badge";
}

function renderAnswer(data) {
  answerCard.classList.remove("hidden");
  answerText.textContent = data.answer;

  strengthBadge.className = badgeClass(data.evidence_strength);
  strengthBadge.textContent = `Evidence: ${data.evidence_strength}`;

  citationsEl.innerHTML = "";
  data.citations.forEach((citation) => {
    const card = document.createElement("div");
    card.className = "citation-card";
    card.innerHTML = `
      <strong>${citation.paper_title}</strong>
      <span class="page-pill">Page ${citation.page_number}</span>
    `;
    citationsEl.appendChild(card);
  });

  evidenceEl.innerHTML = "";
  data.evidence.forEach((chunk, index) => {
    const scores = [];

    scores.push(`Search ${Number(chunk.search_score || 0).toFixed(3)}`);

    if (chunk.keyword_score !== null && chunk.keyword_score !== undefined) {
      scores.push(`Keyword ${Number(chunk.keyword_score).toFixed(3)}`);
    }

    if (chunk.rrf_score !== null && chunk.rrf_score !== undefined) {
      scores.push(`RRF ${Number(chunk.rrf_score).toFixed(4)}`);
    }

    if (chunk.rerank_score !== null && chunk.rerank_score !== undefined) {
      scores.push(`Rerank ${Number(chunk.rerank_score).toFixed(3)}`);
    }

    const card = document.createElement("div");
    card.className = "evidence-card";
    card.innerHTML = `
      <strong>${index + 1}. ${chunk.paper_title}, page ${chunk.page_number}</strong>
      <p>${chunk.text}</p>
      <div class="score-row">
        ${scores.map((score) => `<span class="score-chip">${score}</span>`).join("")}
      </div>
    `;
    evidenceEl.appendChild(card);
  });
}

searchButton.addEventListener("click", search);

document.getElementById("clearButton").addEventListener("click", () => {
  questionEl.value = "";
  questionEl.focus();
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionEl.value = button.dataset.question;
    questionEl.focus();
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
    `Evidence strength: ${lastAnswer.evidence_strength}`,
    "",
    "Citations:",
    ...lastAnswer.citations.map((citation) => `- ${citation.citation}`),
    "",
    "Evidence:",
    ...lastAnswer.evidence.map((chunk, index) => (
      `${index + 1}. ${chunk.paper_title}, page ${chunk.page_number}\n${chunk.text}`
    )),
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