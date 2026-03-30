const form = document.getElementById("analyzeForm");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const modality = document.getElementById("modality");
const statusEl = document.getElementById("status");
const resultCard = document.getElementById("resultCard");
const badge = document.getElementById("badge");
const riskLevel = document.getElementById("riskLevel");
const deepfakeScore = document.getElementById("deepfakeScore");
const confidence = document.getElementById("confidence");
const detectedModality = document.getElementById("detectedModality");
const indicators = document.getElementById("indicators");
const forensicDetails = document.getElementById("forensicDetails");
const meterFill = document.getElementById("meterFill");
const analyzeBtn = document.getElementById("analyzeBtn");
const dropzone = document.getElementById("dropzone");
const briefAnalysis = document.getElementById("briefAnalysis");
const summarySource = document.getElementById("summarySource");

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  fileName.textContent = file ? file.name : "No file selected";
});

// Improve dropzone on mobile
["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    dropzone.classList.remove("dragover");
  });
});

// Better touch feedback
dropzone.addEventListener("touchstart", () => {
  dropzone.style.opacity = "0.95";
});

dropzone.addEventListener("touchend", () => {
  dropzone.style.opacity = "1";
});

// Prevent double-click on buttons
let submitInProgress = false;

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();

  // Prevent double-submit on mobile
  if (submitInProgress) {
    return;
  }

  const file = fileInput.files?.[0];
  if (!file) {
    setStatus("Select a file before analyzing.", true);
    return;
  }

  const body = new FormData();
  body.append("file", file);
  if (modality.value !== "auto") {
    body.append("modality", modality.value);
  }
  body.append("use_google", "true");

  setStatus("Analyzing media, please wait...");
  analyzeBtn.disabled = true;
  submitInProgress = true;

  try {
    const telemetryHeaders = window.SignalScopeClient?.headers || {};
    const res = await fetch("/analyze", {
      method: "POST",
      body,
      headers: telemetryHeaders,
    });

    if (!res.ok) {
      const detail = await readErrorMessage(res);
      throw new Error(detail || "Analysis failed.");
    }

    const data = await res.json();
    renderResult(data);
    setStatus("Analysis complete.");
  } catch (err) {
    setStatus(err.message || "Unexpected error during analysis.", true);
  } finally {
    analyzeBtn.disabled = false;
    submitInProgress = false;
  }
});

function renderResult(data) {
  resultCard.classList.remove("hidden");

  const scorePct = Math.round((data.deepfake_score ?? 0) * 100);
  const confPct = Math.round((data.confidence ?? 0) * 100);

  deepfakeScore.textContent = `${scorePct}%`;
  confidence.textContent = `${confPct}%`;
  riskLevel.textContent = data.risk_level || "-";
  detectedModality.textContent = capitalize(data.modality || "unknown");

  badge.textContent = data.label || "Unknown";
  badge.classList.remove("real", "fake");
  if ((data.label || "").toLowerCase().includes("suspected")) {
    badge.classList.add("fake");
  } else {
    badge.classList.add("real");
  }

  meterFill.style.width = `${scorePct}%`;

  indicators.innerHTML = "";
  const list = Array.isArray(data.indicators) ? data.indicators : [];
  if (!list.length) {
    const li = document.createElement("li");
    li.textContent = "No indicators returned.";
    indicators.appendChild(li);
    return;
  }

  list.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    indicators.appendChild(li);
  });

  forensicDetails.innerHTML = "";
  const details = data.forensic_details && typeof data.forensic_details === "object" ? data.forensic_details : {};
  const entries = Object.entries(details);
  if (!entries.length) {
    const li = document.createElement("li");
    li.textContent = "No forensic metrics returned.";
    forensicDetails.appendChild(li);
  } else {
    entries.forEach(([key, value]) => {
      const li = document.createElement("li");
      li.textContent = `${prettifyKey(key)}: ${value}`;
      forensicDetails.appendChild(li);
    });
  }

  summarySource.textContent = `Summary source: ${String(data.analysis_source || "local")}`;
  briefAnalysis.textContent = data.analysis_summary || buildBriefAnalysis(data, scorePct, confPct);
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#b91c1c" : "#334155";
}

async function readErrorMessage(res) {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
  } catch (_err) {
    return "";
  }
  return "";
}

function capitalize(text) {
  if (!text || typeof text !== "string") {
    return "-";
  }
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function buildBriefAnalysis(data, scorePct, confPct) {
  const isFake = (data.label || "").toLowerCase().includes("suspected");
  const intensity = scorePct >= 75 ? "strong" : scorePct >= 55 ? "moderate" : "low";
  const confidenceBand = confPct >= 75 ? "high" : confPct >= 55 ? "medium" : "limited";
  const indicatorCount = Array.isArray(data.indicators) ? data.indicators.length : 0;

  if (isFake) {
    return `The scan found ${intensity} deepfake-like patterns with ${confidenceBand} confidence across ${indicatorCount} indicator(s). Review source provenance before trusting this media.`;
  }
  return `The scan found ${intensity} manipulation signals and currently classifies this as likely real with ${confidenceBand} confidence. Keep normal verification checks for critical content.`;
}

function prettifyKey(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
