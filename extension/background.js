// Netflix IMDb Rating Extension - Background Service Worker
// Backend origin is supplied by a private backend-config.js file.

let BACKEND_URL = "";
try {
  importScripts("backend-config.js");
  BACKEND_URL = (self.NETFLIX_IMDB_BACKEND_URL || "").trim().replace(/\/+$/, "");
} catch (error) {
  // The example config is not used automatically; the private config is local or packaged separately.
}
const memoryCache = new Map();

function hasNumericRating(item) {
  const rating = Number(item?.rating);
  return Number.isFinite(rating) && rating > 0 && rating <= 10;
}

// Load only usable ratings and discard stale N/A entries from older extension versions.
chrome.storage.local.get(["cachedRatings"], (result) => {
  const cachedRatings = result.cachedRatings || {};
  let changed = false;
  for (const [key, val] of Object.entries(cachedRatings)) {
    if (hasNumericRating(val)) {
      memoryCache.set(key, val);
    } else {
      delete cachedRatings[key];
      changed = true;
    }
  }
  if (changed) chrome.storage.local.set({ cachedRatings });
});

// Save only a rating that can be displayed.
function persistRating(title, data) {
  if (!hasNumericRating(data)) return;
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
  if (!BACKEND_URL) {
    return { success: false, error: "Backend URL is not configured", isOffline: true };
  }

  // Check in-memory cache first
  if (memoryCache.has(normTitle)) {
    const cached = memoryCache.get(normTitle);
    if (hasNumericRating(cached)) {
      return { success: true, data: cached, fromCache: true };
    }
    memoryCache.delete(normTitle);
  }

  try {
    const url = `${BACKEND_URL}/api/rating?title=${encodeURIComponent(title.trim())}`;
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
    if (data.success && hasNumericRating(data)) {
      persistRating(title, data);
      return { success: true, data: data };
    } else {
      return { success: false, error: data.error || "Not found" };
    }
  } catch (err) {
    const isOffline = err.name === "AbortError" || err.message?.includes("Failed to fetch");
    return {
      success: false,
      error: isOffline ? "Rating service unavailable" : err.message,
      isOffline: true
    };
  }
}

// Check server status
async function checkBackendStatus() {
  if (!BACKEND_URL) return { online: false };
  try {
    const response = await fetch(`${BACKEND_URL}/api/status`, { cache: "no-store" });
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
