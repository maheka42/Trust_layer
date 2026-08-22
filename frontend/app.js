const API_BASE = "http://127.0.0.1:8000";

const els = {
  banner: document.getElementById("error-banner"),
  status: document.getElementById("backend-status"),
  total: document.getElementById("stat-total"),
  allow: document.getElementById("stat-allow"),
  review: document.getElementById("stat-review"),
  block: document.getElementById("stat-block"),
  fraud: document.getElementById("stat-fraud"),
  trap: document.getElementById("stat-trap"),
  txnBody: document.getElementById("txn-body"),
  txnCount: document.getElementById("txn-count"),
  txnEmpty: document.getElementById("txn-empty"),
  hint: document.getElementById("investigate-hint"),
  log: document.getElementById("log"),
  pulse: document.getElementById("pulse"),
  result: document.getElementById("result"),
  score: document.getElementById("risk-score"),
  decision: document.getElementById("decision-badge"),
  signals: document.getElementById("signals"),
  signalSum: document.getElementById("signal-sum"),
  explanation: document.getElementById("explanation"),
  explanationSource: document.getElementById("explanation-source"),
  details: document.getElementById("details"),
  fraudCaught: document.getElementById("eval-fraud-caught"),
  fraudCaughtPct: document.getElementById("eval-fraud-caught-pct"),
  fraudMissed: document.getElementById("eval-fraud-missed"),
  fraudMissedPct: document.getElementById("eval-fraud-missed-pct"),
  trapOk: document.getElementById("eval-trap-ok"),
  trapOkPct: document.getElementById("eval-trap-ok-pct"),
  trapFlag: document.getElementById("eval-trap-flag"),
  trapFlagPct: document.getElementById("eval-trap-flag-pct"),
  primaryDriver: document.getElementById("primary-driver"),
};

let eventSource = null;
let selectedId = null;
let investigationDone = false;
const STEP_MESSAGES = [
  "Checking user history...",
  "Checking previous chargebacks...",
  "Checking device...",
  "Checking merchant...",
  "Calculating risk score...",
  "Making decision...",
  "Generating explanation...",
  "Investigation complete.",
];

function showBanner(message) {
  els.banner.textContent = message;
  els.banner.classList.remove("hidden");
}

function hideBanner() {
  els.banner.classList.add("hidden");
}

function pct(value) {
  if (value === null || value === undefined) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function capitalizeDriver(value) {
  return String(value)
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatAmount(amount, currency) {
  const n = Number(amount);
  if (Number.isNaN(n)) return String(amount);
  return `${n.toFixed(2)} ${currency || ""}`.trim();
}

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json();
}

async function loadStats() {
  const stats = await fetchJson("/stats");
  els.total.textContent = stats.total_transactions;
  els.allow.textContent = stats.allow_count;
  els.review.textContent = stats.review_count;
  els.block.textContent = stats.block_count;
  els.fraud.textContent = pct(stats.fraud_caught_rate);
  els.trap.textContent = pct(stats.trap_allowed_rate);
  const fraudTotal = Number(stats.fraud_transaction_count) || 0;
  const trapTotal = Number(stats.trap_transaction_count) || 0;
  els.fraudCaught.textContent = stats.fraud_caught ?? "—";
  els.fraudMissed.textContent = stats.fraud_missed ?? "—";
  els.trapOk.textContent = stats.trap_correctly_allowed ?? "—";
  els.trapFlag.textContent = stats.trap_incorrectly_flagged ?? "—";
  els.fraudCaughtPct.textContent = fraudTotal ? pct((stats.fraud_caught || 0) / fraudTotal) : "";
  els.fraudMissedPct.textContent = fraudTotal ? pct((stats.fraud_missed || 0) / fraudTotal) : "";
  els.trapOkPct.textContent = trapTotal ? pct((stats.trap_correctly_allowed || 0) / trapTotal) : "";
  els.trapFlagPct.textContent = trapTotal ? pct((stats.trap_incorrectly_flagged || 0) / trapTotal) : "";
}

function renderTransactions(rows) {
  els.txnBody.innerHTML = "";
  if (!rows.length) {
    els.txnEmpty.classList.remove("hidden");
    els.txnCount.textContent = "";
    return;
  }
  els.txnEmpty.classList.add("hidden");
  els.txnCount.textContent = `${rows.length} records`;
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.id = row.id;
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.user_id}</td>
      <td>${formatAmount(row.amount, row.currency)}</td>
      <td>${row.merchant || ""}</td>
      <td>${row.city || ""}</td>
      <td>${row.timestamp || ""}</td>
      <td><span class="gt ${row.ground_truth}">${(row.ground_truth || "").toUpperCase()}</span></td>
      <td><button class="investigate-btn" type="button" data-id="${row.id}">Investigate</button></td>
    `;
    tr.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      selectRow(row.id);
    });
    els.txnBody.appendChild(tr);
  }
}

function selectRow(transactionId) {
  selectedId = transactionId;
  for (const row of els.txnBody.querySelectorAll("tr")) {
    row.classList.toggle("selected", row.dataset.id === transactionId);
  }
  els.hint.textContent = `Selected ${transactionId}. Click Investigate to run the agent pipeline.`;
}

function startInvestigation(transactionId) {
  selectRow(transactionId);
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  els.result.classList.add("hidden");
  els.log.textContent = "";
  els.pulse.classList.remove("hidden");
  els.hint.textContent = `Investigating ${transactionId}...`;
  const seen = new Set();

  investigationDone = false;
  eventSource = new EventSource(`${API_BASE}/investigate/${encodeURIComponent(transactionId)}`);

  eventSource.onmessage = (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch (error) {
      appendLog("! Could not parse investigation event.");
      return;
    }
    const message = payload.message || "";
    if (STEP_MESSAGES.includes(message) && !seen.has(message)) {
      seen.add(message);
      appendLog(`✓ ${message}`);
    }
    if (message === "Investigation complete." && payload.result) {
      investigationDone = true;
      renderResult(payload.result);
      stopInvestigation();
    }
  };

  eventSource.onerror = () => {
    if (!investigationDone) {
      showBanner("SSE connection failed. Check that FastAPI is running at http://127.0.0.1:8000");
      appendLog("! SSE connection failed.");
    }
    stopInvestigation();
  };
}

function stopInvestigation() {
  els.pulse.classList.add("hidden");
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function appendLog(line) {
  els.log.textContent = els.log.textContent ? `${els.log.textContent}\n${line}` : line;
  els.log.scrollTop = els.log.scrollHeight;
}

function renderResult(result) {
  els.result.classList.remove("hidden");
  const score = Number(result.risk_score);
  const decision = result.decision || "—";
  els.score.textContent = Number.isNaN(score) ? "—" : String(score);
  els.decision.textContent = decision;
  els.decision.className = `decision ${decision}`;
  if (decision === "REVIEW" && result.primary_driver) {
    els.primaryDriver.textContent = `Primary driver: ${capitalizeDriver(result.primary_driver)}`;
    els.primaryDriver.classList.remove("hidden");
  } else {
    els.primaryDriver.textContent = "";
    els.primaryDriver.classList.add("hidden");
  }

  const signals = Array.isArray(result.signals) ? result.signals : [];
  els.signals.innerHTML = "";
  let sum = 0;
  if (!signals.length) {
    els.signals.innerHTML = `<p class="muted">No risk points were added.</p>`;
  } else {
    for (const signal of signals) {
      sum += Number(signal.weight) || 0;
      const item = document.createElement("article");
      item.className = "signal";
      item.innerHTML = `
        <div>
          <h4>${String(signal.name || "").replaceAll("_", " ").toUpperCase()}</h4>
          <p>${signal.description || ""}</p>
        </div>
        <div class="points">+${signal.weight}</div>
      `;
      els.signals.appendChild(item);
    }
  }
  els.signalSum.textContent = `Risk score = sum of triggered signals (${sum})`;

  els.explanation.textContent = result.explanation || "No explanation returned.";
  const source = result.explanation_source;
  if (source === "groq") {
    els.explanationSource.textContent = "Explanation source: Groq LLM";
  } else if (source === "local_fallback") {
    els.explanationSource.textContent = "Explanation source: Local fallback";
  } else {
    els.explanationSource.textContent = source ? `Explanation source: ${source}` : "";
  }

  const txn = result.transaction || {};
  const fields = [
    ["Transaction ID", txn.id],
    ["User", txn.user_id],
    ["Amount", formatAmount(txn.amount, txn.currency)],
    ["Currency", txn.currency],
    ["Merchant", txn.merchant],
    ["Device", txn.device_id],
    ["Timestamp", txn.timestamp],
    ["City", txn.city],
    ["Country", txn.country],
    ["Payment method", txn.payment_method],
    ["Channel", txn.channel],
  ];
  els.details.innerHTML = fields
    .map(([label, value]) => `<dt>${label}</dt><dd>${value ?? "—"}</dd>`)
    .join("");
}

els.txnBody.addEventListener("click", (event) => {
  const button = event.target.closest(".investigate-btn");
  if (!button) return;
  event.stopPropagation();
  startInvestigation(button.dataset.id);
});

async function init() {
  try {
    await loadStats();
    const rows = await fetchJson("/transactions");
    renderTransactions(rows);
    els.status.textContent = "Backend connected";
    els.status.classList.add("ok");
    hideBanner();
  } catch (error) {
    els.status.textContent = "Backend unavailable";
    els.status.classList.add("bad");
    showBanner("Backend unavailable. Start FastAPI at http://127.0.0.1:8000");
  }
}

init();
