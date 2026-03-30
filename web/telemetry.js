(function () {
  function detectOS(ua) {
    const lower = (ua || "").toLowerCase();
    if (lower.includes("windows")) return "Windows";
    if (lower.includes("android")) return "Android";
    if (lower.includes("iphone") || lower.includes("ipad") || lower.includes("ios")) return "iOS";
    if (lower.includes("mac os") || lower.includes("macintosh")) return "macOS";
    if (lower.includes("linux")) return "Linux";
    return "Unknown";
  }

  function detectBrowser(ua) {
    const lower = (ua || "").toLowerCase();
    if (lower.includes("edg/")) return "Edge";
    if (lower.includes("chrome/") && !lower.includes("edg/")) return "Chrome";
    if (lower.includes("firefox/")) return "Firefox";
    if (lower.includes("safari/") && !lower.includes("chrome/")) return "Safari";
    return "Unknown";
  }

  function inferSystemName() {
    const uaData = navigator.userAgentData;
    if (uaData && typeof uaData.platform === "string" && uaData.platform.trim()) {
      return uaData.platform.trim();
    }
    if (typeof navigator.platform === "string" && navigator.platform.trim()) {
      return navigator.platform.trim();
    }
    return "Unknown";
  }

  const info = {
    os_name: detectOS(navigator.userAgent || ""),
    browser_name: detectBrowser(navigator.userAgent || ""),
    system_name: inferSystemName(),
    page: window.location.pathname,
  };

  window.SignalScopeClient = {
    headers: {
      "X-Client-OS": info.os_name,
      "X-Client-Browser": info.browser_name,
      "X-Client-System": info.system_name,
      "X-Page-Path": info.page,
    },
  };

  const form = new FormData();
  form.append("os_name", info.os_name);
  form.append("browser_name", info.browser_name);
  form.append("system_name", info.system_name);
  form.append("page", info.page);

  fetch("/telemetry/client", {
    method: "POST",
    body: form,
    headers: window.SignalScopeClient.headers,
  }).catch(() => {
    // Telemetry is non-critical.
  });
})();
