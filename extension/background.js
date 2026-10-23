// Netflix IMDb Rating Extension - Background Service Worker
// Communicates with local Python server (http://127.0.0.1:5000)

const BACKEND_URL = "http://127.0.0.1:5000";
const memoryCache = new Map();

// Load cache from chrome.storage on startup
chrome.storage.local.get(["cachedRatings"], (result) => {
  if (result.cachedRatings) {
    for (const [key, val] of Object.entries(result.cachedRatings)) {
      memoryCache.set(key, val);
    }
  }
});

// Save rating to persistent chrome.storage
function persistRating(title, data) {
  memoryCache.set(title.toLowerCase(), data);
  chrome.storage.local.get(["cachedRatings"], (result) => {
    const store = result.cachedRatings || {};
    store[title.toLowerCase()] = data;
    chrome.storage.local.set({ cachedRatings: store });
  });
}

// Fetch rating from local Python server
async function fetchRatingFromPython(title) {
  const normTitle = title.trim().toLowerCase();

  // Check in-memory cache first
  if (memoryCache.has(normTitle)) {
    return { success: true, data: memoryCache.get(normTitle), fromCache: true };
  }

  try {
    const url = `${BACKEND_URL}/rating?title=${encodeURIComponent(title.trim())}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    const response = await fetch(url, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` };
    }

    const data = await response.json();
    if (data.success) {
      persistRating(title, data);
      return { success: true, data: data };
    } else {
      return { success: false, error: data.error || "Not found" };
    }
  } catch (err) {
    const isOffline = err.name === "AbortError" || err.message?.includes("Failed to fetch");
    return {
      success: false,
      error: isOffline ? "Python backend offline" : err.message,
      isOffline: true
    };
  }
}

// Check server status
async function checkBackendStatus() {
  try {
    const response = await fetch(`${BACKEND_URL}/status`, { cache: "no-store" });
    if (response.ok) {
      const data = await response.json();
      return { online: true, ...data };
    }
  } catch (e) {
    // server unreachable
  }
  return { online: false };
}

// Message Router
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_RATING") {
    fetchRatingFromPython(request.title).then(sendResponse);
    return true; // Keep channel open for async response
  }

  if (request.action === "CHECK_STATUS") {
    checkBackendStatus().then(sendResponse);
    return true;
  }

  if (request.action === "CLEAR_CACHE") {
    memoryCache.clear();
    chrome.storage.local.remove(["cachedRatings"], () => {
      sendResponse({ success: true });
    });
    return true;
  }
});
