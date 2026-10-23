// Netflix IMDb Rating Extension - Content Script
// Detects cursor hover on Netflix movie cards and displays IMDb ratings

(() => {
  "use strict";

  // Prevent multiple injections
  if (window.__netflix_imdb_injected) return;
  window.__netflix_imdb_injected = true;

  const BADGE_CLASS = "netflix-imdb-badge";
  const TOOLTIP_ID = "netflix-imdb-floating-tooltip";
  let hoverTimer = null;
  let activeCard = null;
  let floatingTooltip = null;

  // --- Initialize Floating Tooltip Element ---
  function getOrCreateTooltip() {
    let tooltip = document.getElementById(TOOLTIP_ID);
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = TOOLTIP_ID;
      tooltip.className = "netflix-imdb-tooltip hidden";
      document.body.appendChild(tooltip);
    }
    return tooltip;
  }

  // --- Title Extraction ---
  function extractTitleFromElement(el) {
    if (!el) return null;

    // 1. Look for image alt text
    const img = el.querySelector("img.boxart-image, img[alt], .previewModal--boxart");
    if (img && img.alt && img.alt.trim().length > 0) {
      return cleanTitle(img.alt);
    }

    // 2. Look for aria-label on links or cards
    const ariaEl = el.hasAttribute("aria-label") ? el : el.querySelector("[aria-label]");
    if (ariaEl && ariaEl.getAttribute("aria-label")) {
      const label = ariaEl.getAttribute("aria-label").trim();
      if (label && !label.toLowerCase().startsWith("play") && !label.toLowerCase().startsWith("more info")) {
        return cleanTitle(label);
      }
    }

    // 3. Look for fallback title text or preview modal title
    const titleTextEl = el.querySelector(
      ".fallback-text, [data-uia='previewModal--player-title'], .previewModal--player-title, .video-artwork-title"
    );
    if (titleTextEl && titleTextEl.textContent) {
      return cleanTitle(titleTextEl.textContent);
    }

    return null;
  }

  function cleanTitle(raw) {
    if (!raw) return "";
    let t = raw.trim();
    t = t.replace(/^Watch\s+/i, "");
    t = t.replace(/\s+on\s+Netflix$/i, "");
    t = t.replace(/\s*:\s*(Season|Part)\s*\d+.*$/i, "");
    t = t.replace(/\s*\((Season|\d{4}|Limited Series|Miniseries)[^\)]*\)/gi, "");
    return t.trim();
  }

  // --- Badge Creation & Injection ---
  function attachBadgeToCard(card, title) {
    if (!card || card.querySelector(`.${BADGE_CLASS}`)) return;

    // Ensure relative positioning for accurate absolute badge placement
    const computedStyle = window.getComputedStyle(card);
    if (computedStyle.position === "static") {
      card.style.position = "relative";
    }

    const badge = document.createElement("div");
    badge.className = `${BADGE_CLASS} netflix-imdb-badge-loading`;
    badge.innerHTML = `
      <span class="imdb-icon">IMDb</span>
      <span class="imdb-score"><span class="imdb-spinner"></span></span>
    `;

    card.appendChild(badge);

    // Request rating from background worker
    chrome.runtime.sendMessage({ action: "GET_RATING", title: title }, (response) => {
      if (!badge.isConnected) return;

      badge.classList.remove("netflix-imdb-badge-loading");

      if (response && response.success && response.data) {
        const item = response.data;
        const isRated = item.rating && item.rating !== "N/A";
        const scoreText = isRated ? `★ ${item.rating}` : "Unrated";
        badge.innerHTML = `
          <span class="imdb-icon">IMDb</span>
          <span class="imdb-score">${scoreText}</span>
        `;
        badge.dataset.title = item.title || title;
        badge.dataset.rating = item.rating || "N/A";
        badge.dataset.votes = item.votes || "";
        badge.dataset.year = item.year || "";
        badge.dataset.genre = item.genre || "";
        badge.dataset.plot = item.plot || "";
        badge.dataset.imdbId = item.imdb_id || "";

        // Event listener to show rich tooltip on badge hover
        badge.addEventListener("mouseenter", (e) => {
          showTooltip(badge, e);
        });
        badge.addEventListener("mouseleave", () => {
          hideTooltip();
        });
      } else if (response && response.isOffline) {
        badge.classList.add("netflix-imdb-offline");
        badge.title = "Python server offline. Run: python3 server.py";
        badge.innerHTML = `
          <span class="imdb-icon">IMDb</span>
          <span class="imdb-score">Offline ⚠️</span>
        `;
      } else {
        badge.classList.add("netflix-imdb-notfound");
        badge.innerHTML = `
          <span class="imdb-icon">IMDb</span>
          <span class="imdb-score">N/A</span>
        `;
      }
    });
  }

  // --- Floating Tooltip Display ---
  function showTooltip(badge, event) {
    const tooltip = getOrCreateTooltip();
    const data = badge.dataset;
    if (!data.title) return;

    const imdbUrl = data.imdbId ? `https://www.imdb.com/title/${data.imdbId}/` : `https://www.imdb.com/find?q=${encodeURIComponent(data.title)}`;

    tooltip.innerHTML = `
      <div class="tooltip-header">
        <div class="tooltip-title-row">
          <strong class="tooltip-title">${escapeHtml(data.title)}</strong>
          ${data.year && data.year !== "N/A" ? `<span class="tooltip-year">(${escapeHtml(data.year)})</span>` : ""}
        </div>
        <div class="tooltip-rating-badge">
          <span class="tooltip-imdb-logo">IMDb</span>
          <span class="tooltip-rating-num">★ ${escapeHtml(data.rating)}</span>
          <span class="tooltip-rating-scale">/10</span>
        </div>
      </div>
      ${data.votes && data.votes !== "N/A" ? `<div class="tooltip-votes">👥 ${escapeHtml(data.votes)} votes</div>` : ""}
      ${data.genre && data.genre !== "N/A" ? `<div class="tooltip-genres">${escapeHtml(data.genre)}</div>` : ""}
      ${data.plot ? `<p class="tooltip-plot">${escapeHtml(data.plot)}</p>` : ""}
      <div class="tooltip-footer">
        <a href="${imdbUrl}" target="_blank" rel="noopener noreferrer" class="tooltip-link">
          View on IMDb ↗
        </a>
      </div>
    `;

    tooltip.classList.remove("hidden");

    // Position tooltip right below or above badge
    const rect = badge.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let top = rect.bottom + 8;
    let left = rect.left;

    // Flip upward if near bottom of viewport
    if (top + tooltipRect.height > window.innerHeight) {
      top = rect.top - tooltipRect.height - 8;
    }
    // Constrain horizontally
    if (left + tooltipRect.width > window.innerWidth - 16) {
      left = window.innerWidth - tooltipRect.width - 16;
    }
    if (left < 16) left = 16;

    tooltip.style.top = `${Math.max(8, top + window.scrollY)}px`;
    tooltip.style.left = `${left + window.scrollX}px`;
  }

  function hideTooltip() {
    if (floatingTooltip) {
      floatingTooltip.classList.add("hidden");
    }
    const tooltip = document.getElementById(TOOLTIP_ID);
    if (tooltip) {
      tooltip.classList.add("hidden");
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // --- Handle Netflix Preview Modal Integration ---
  function checkAndEnhancePreviewModal(modal) {
    if (!modal || modal.querySelector(".netflix-imdb-modal-rating")) return;

    const title = extractTitleFromElement(modal);
    if (!title) return;

    // Target the metadata row in preview modal (where match %, year, rating icons are)
    const metaContainer = modal.querySelector(".previewModal--detailsMetadata-left, .videoMetadata--container");
    if (!metaContainer) return;

    const modalBadge = document.createElement("div");
    modalBadge.className = "netflix-imdb-modal-rating";
    modalBadge.innerHTML = `
      <span class="imdb-icon">IMDb</span>
      <span class="imdb-score"><span class="imdb-spinner"></span></span>
    `;
    metaContainer.prepend(modalBadge);

    chrome.runtime.sendMessage({ action: "GET_RATING", title: title }, (response) => {
      if (!modalBadge.isConnected) return;
      if (response && response.success && response.data) {
        const item = response.data;
        const url = item.imdb_id ? `https://www.imdb.com/title/${item.imdb_id}/` : `https://www.imdb.com/find?q=${encodeURIComponent(item.title)}`;
        modalBadge.innerHTML = `
          <a href="${url}" target="_blank" rel="noopener noreferrer" class="imdb-modal-link">
            <span class="imdb-icon">IMDb</span>
            <span class="imdb-score">★ ${item.rating}/10</span>
            ${item.votes && item.votes !== "N/A" ? `<span class="imdb-votes">(${item.votes})</span>` : ""}
          </a>
        `;
      } else {
        modalBadge.style.display = "none";
      }
    });
  }

  // --- Mouseover / Hover Delegated Listener ---
  document.addEventListener("mouseover", (event) => {
    // 1. Check for Preview Modal
    const modal = event.target.closest(".previewModal--container, .previewModal--info");
    if (modal) {
      checkAndEnhancePreviewModal(modal);
    }

    // 2. Check for Movie Cards (Browse Row, Search Grid, etc.)
    const card = event.target.closest(
      ".title-card, .title-card-container, .slider-item, [data-uia*='title-card'], .galleryContent .slider-refocus"
    );

    if (!card) return;
    if (card === activeCard) return;

    activeCard = card;
    clearTimeout(hoverTimer);

    // 260ms hover debounce so quick cursor movements across rows don't spam requests
    hoverTimer = setTimeout(() => {
      const title = extractTitleFromElement(card);
      if (title) {
        attachBadgeToCard(card, title);
      }
    }, 260);
  }, { passive: true });

  document.addEventListener("mouseout", (event) => {
    const card = event.target.closest(".title-card, .title-card-container, .slider-item");
    if (card && card === activeCard) {
      clearTimeout(hoverTimer);
      activeCard = null;
    }
  }, { passive: true });

  console.log("🎬 Netflix IMDb Ratings Extension loaded & active!");
})();
