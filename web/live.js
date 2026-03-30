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
const liveSource = document.getElementById("liveSource");

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
    // Mobile and desktop camera constraints
    const constraints = {
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    };

    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = mediaStream;
    
    // Handle orientation changes on mobile
    window.addEventListener("orientationchange", () => {
      if (mediaStream) {
        setTimeout(() => {
          video.width = video.videoWidth;
          video.height = video.videoHeight;
        }, 100);
      }
    });

    startBtn.disabled = true;
    stopBtn.disabled = false;
    setLiveStatus("Camera active. Running periodic frame analysis...");
    startTimer();
  } catch (err) {
    const errorMsg = err.message || "unknown error";
    let userMsg = `Could not access camera: ${errorMsg}`;
    
    // Provide better error messages for mobile
    if (errorMsg.includes("Permission denied")) {
      userMsg = "Camera permission denied. Please allow camera access in settings.";
    } else if (errorMsg.includes("NotAllowedError")) {
      userMsg = "Camera access not allowed. Check app permissions.";
    } else if (errorMsg.includes("NotFoundError")) {
      userMsg = "No camera device found on this device.";
    }
    
    setLiveStatus(userMsg, true);
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
    body.append("use_google", "true");
    const telemetryHeaders = window.SignalScopeClient?.headers || {};

    const res = await fetch("/analyze-frame", {
      method: "POST",
      body,
      headers: telemetryHeaders,
      // Add timeout for mobile networks
      signal: AbortSignal.timeout(15000),
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
    liveSource.textContent = data.analysis_source || "local";
    liveBrief.textContent = data.analysis_summary || buildBrief(data, scorePct, confPct);
    
    // Add visual feedback on mobile
    liveStatus.style.color = "#166534";
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
