/**
 * Mobile helper - Improves mobile experience
 */

// Prevent zoom on input focus (iOS)
const inputs = document.querySelectorAll("input, select, button, textarea");
inputs.forEach((input) => {
  input.addEventListener("focus", () => {
    document.body.style.zoom = "1";
  });
});

// Handle safe areas for notched devices
function updateSafeArea() {
  const topSafeArea = getComputedStyle(document.documentElement).getPropertyValue("--safe-area-inset-top") || "0px";
  const bottomSafeArea = getComputedStyle(document.documentElement).getPropertyValue("--safe-area-inset-bottom") || "0px";
  
  if (navigator.standalone === true) {
    document.body.style.paddingTop = topSafeArea;
    document.body.style.paddingBottom = bottomSafeArea;
  }
}

// Initialize on load
window.addEventListener("load", updateSafeArea);
window.addEventListener("orientationchange", updateSafeArea);

// Disable pull-to-refresh on mobile Safari if desired
document.addEventListener("touchmove", (e) => {
  if (e.touches.length > 1) {
    e.preventDefault();
  }
});

// Improve keyboard behavior on mobile
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.activeElement?.blur?.();
  }
});

// Log mobile environment info
if (navigator.userAgent.match(/mobile|android|iphone|ipad|ipod/i)) {
  console.log(
    "%c📱 Mobile Environment",
    "color: #0f6d74; font-weight: bold; font-size: 14px",
    {
      userAgent: navigator.userAgent,
      standalone: navigator.standalone,
      maxTouchPoints: navigator.maxTouchPoints,
      deviceMemory: navigator.deviceMemory,
      connection: navigator.connection?.effectiveType,
    }
  );
}
