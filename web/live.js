const video = document.getElementById("liveVideo");
const canvas = document.getElementById("captureCanvas");
const startBtn = document.getElementById("startCamBtn");
const stopBtn = document.getElementById("stopCamBtn");
const intervalRange = document.getElementById("intervalRange");
const liveStatus = document.getElementById("liveStatus");
const liveVerdict = document.getElementById("liveVerdict");
const liveScore = document.getElementById("liveScore");
const liveConfidence = document.getElementById("liveConfidence");
const liveBrief = document.getElementById("liveBrief");

let mediaStream = null;
let timerId = null;
let busy = false;

startBtn.addEventListener("click", startCameraAnalysis);
stopBtn.addEventListener("click", stopCameraAnalysis);

async function startCameraAnalysis() {
  if (mediaStream) {
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    });
    video.srcObject = mediaStream;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setLiveStatus("Camera active. Running periodic frame analysis...");
    startTimer();
  } catch (err) {
    setLiveStatus(`Could not access camera: ${err.message || "unknown error"}`, true);
  }
}

function stopCameraAnalysis() {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  video.srcObject = null;
  startBtn.disabled = false;
  stopBtn.disabled = true;
  setLiveStatus("Camera stopped.");
}

function startTimer() {
  if (timerId) {
    clearInterval(timerId);
  }

  const intervalMs = Number(intervalRange.value) * 1000;
  timerId = setInterval(() => {
    void analyzeCurrentFrame();
  }, intervalMs);

  void analyzeCurrentFrame();
}

intervalRange.addEventListener("change", () => {
  if (mediaStream) {
    startTimer();
  }
});

async function analyzeCurrentFrame() {
  if (!mediaStream || busy || video.videoWidth === 0 || video.videoHeight === 0) {
    return;
  }

  busy = true;
  try {
    const blob = await captureFrameBlob();
    const body = new FormData();
    body.append("file", blob, "frame.jpg");

    const res = await fetch("/analyze-frame", {
      method: "POST",
      body,
    });

    if (!res.ok) {
      throw new Error(await readErrorMessage(res));
    }

    const data = await res.json();
    const scorePct = Math.round((data.deepfake_score ?? 0) * 100);
    const confPct = Math.round((data.confidence ?? 0) * 100);
    liveVerdict.textContent = data.label || "-";
    liveScore.textContent = `${scorePct}%`;
    liveConfidence.textContent = `${confPct}%`;
    liveBrief.textContent = buildBrief(data, scorePct, confPct);
    setLiveStatus(`Live scan updated (${new Date().toLocaleTimeString()}).`);
  } catch (err) {
    setLiveStatus(err.message || "Live analysis failed.", true);
  } finally {
    busy = false;
  }
}

function captureFrameBlob() {
  return new Promise((resolve, reject) => {
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      reject(new Error("Canvas is unavailable"));
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Could not capture frame"));
          return;
        }
        resolve(blob);
      },
      "image/jpeg",
      0.85,
    );
  });
}

function setLiveStatus(message, isError = false) {
  liveStatus.textContent = message;
  liveStatus.style.color = isError ? "#b91c1c" : "#334155";
}

async function readErrorMessage(res) {
  try {
    const data = await res.json();
    return data?.detail || "Live analysis failed";
  } catch (_err) {
    return "Live analysis failed";
  }
}

function buildBrief(data, scorePct, confPct) {
  const maybeFake = (data.label || "").toLowerCase().includes("suspected");
  if (maybeFake) {
    return `Possible manipulation patterns are being observed (${scorePct}% score, ${confPct}% confidence). Consider identity verification checks.`;
  }
  return `Current frame appears likely authentic (${scorePct}% score, ${confPct}% confidence). Continue monitoring for consistency.`;
}

window.addEventListener("beforeunload", () => {
  stopCameraAnalysis();
});
