// Netflix IMDb Ratings Popup Logic

document.addEventListener("DOMContentLoaded", () => {
  const dot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const statusSubtext = document.getElementById("status-subtext");
  const testInput = document.getElementById("test-input");
  const testBtn = document.getElementById("test-btn");
  const testResult = document.getElementById("test-result");
  const clearCacheBtn = document.getElementById("clear-cache-btn");

  // Check Backend Status
  function checkStatus() {
    chrome.runtime.sendMessage({ action: "CHECK_STATUS" }, (res) => {
      if (res && res.online) {
        dot.className = "dot online";
        statusText.textContent = "Python Backend Connected";
        statusSubtext.textContent = `Cached titles: ${res.cached_titles || 0} (Port 5000)`;
      } else {
        dot.className = "dot offline";
        statusText.textContent = "Python Backend Offline";
        statusSubtext.textContent = "Run: python3 backend/server.py";
      }
    });
  }

  // Initial status check
  checkStatus();

  // Test Movie Search
  testBtn.addEventListener("click", () => {
    const title = testInput.value.trim();
    if (!title) return;

    testResult.classList.remove("hidden");
    testResult.innerHTML = `<span style="color:#f5c518;">Searching IMDb for "${title}"...</span>`;

    chrome.runtime.sendMessage({ action: "GET_RATING", title: title }, (res) => {
      if (res && res.success && res.data) {
        const d = res.data;
        testResult.innerHTML = `
          <div class="result-title">${d.title} (${d.year || "N/A"})</div>
          <div class="result-rating">★ ${d.rating}/10 <span style="font-size:11px;color:#888;">(${d.votes || "0"} votes)</span></div>
          <div style="color:#aaa;font-size:11px;margin-top:4px;">${d.genre || ""}</div>
        `;
        checkStatus(); // update cached count
      } else {
        testResult.innerHTML = `
          <div style="color:#ff6b6b;">⚠️ ${res?.error || "Movie not found or backend offline"}</div>
        `;
      }
    });
  });

  testInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") testBtn.click();
  });

  // Clear Cache
  clearCacheBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "CLEAR_CACHE" }, () => {
      clearCacheBtn.textContent = "Cache Cleared!";
      setTimeout(() => {
        clearCacheBtn.textContent = "Clear Cache";
      }, 1500);
      checkStatus();
    });
  });
});
