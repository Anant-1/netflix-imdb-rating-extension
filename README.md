# 🎬 Netflix IMDb Rating On Hover (Chrome Extension + Python)

A Chrome Extension that displays **IMDb ratings, vote counts, release years, and movie summaries** whenever you hover your cursor over any movie or TV show on **Netflix**.

Powered by a lightweight **Python backend** running locally on your machine with built-in SQLite caching.

---

## 🌟 Features

- **Hover to View Rating**: Hover your cursor over any movie card or carousel item on Netflix to reveal an instant golden IMDb rating badge.
- **Rich Hover Tooltip**: Hover over the badge for complete details: Star rating (`★ 8.8/10`), total IMDb votes, release year, genres, plot description, and direct link to the IMDb page.
- **Netflix Preview Modal Integration**: Seamlessly integrates into Netflix's expanded preview drawer alongside Match %, Maturity Rating, and HD badges.
- **Zero Python Dependencies**: The Python backend uses standard libraries (`http.server`, `urllib`, `sqlite3`). No need for `pip install` or complex virtual environments!
- **Instant SQLite Caching**: Ratings are automatically cached locally so repeated hovers load with 0ms delay.
- **Interactive Popup**: Test searches, check backend connection status, and clear cache anytime from the Chrome toolbar icon.
- **Optional OMDb API Support**: Works out of the box with direct IMDb search scraping, with optional support for OMDb API keys if desired.

---

## 🚀 Quick Start Guide

### Step 1: Start the Python Backend Server

Open your terminal and run:

```bash
cd /Users/anant/.gemini/antigravity/scratch/netflix-imdb-rating-extension/backend
python3 server.py
```

You should see:
```text
============================================================
🎬 Netflix IMDb Rating Backend Server
============================================================
🚀 Running at: http://127.0.0.1:5000
📡 Ready to accept requests from Chrome Extension
📦 Local Cache: ratings_cache.db
🌐 Mode: Direct IMDb Scraping & Suggestion API (Free, no key needed)
============================================================
```

> **Quick Terminal Test**: You can also test any movie rating from your terminal:
> ```bash
> python3 test_lookup.py "Inception"
> python3 test_lookup.py "Stranger Things"
> ```

---

### Step 2: Load the Extension into Google Chrome

1. Open **Google Chrome** and navigate to:
   ```text
   chrome://extensions/
   ```
2. Enable **Developer mode** using the toggle switch in the top-right corner.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `extension` folder located at:
   ```text
   /Users/anant/.gemini/antigravity/scratch/netflix-imdb-rating-extension/extension
   ```
5. You will see **"Netflix IMDb Ratings Hover"** appear in your extension list!

---

### Step 3: Browse Netflix!

1. Open [Netflix.com](https://www.netflix.com) and log in.
2. Hover your mouse cursor over any movie or series tile.
3. An **IMDb badge** will appear in the top-right corner showing the star rating (e.g. `★ 8.7`).
4. Hover over the badge to see the detailed popup with votes, genres, and synopsis.

---

## 📁 Project Structure

```text
netflix-imdb-rating-extension/
├── backend/
│   ├── server.py             # Python HTTP server (threading, CORS, caching, IMDb lookup)
│   ├── test_lookup.py        # CLI tester for instant movie rating checks
│   ├── ratings_cache.db      # SQLite cache database (created automatically)
│   └── requirements.txt      # Information & optional dependencies
│
├── extension/
│   ├── manifest.json         # Chrome Extension Manifest V3 configuration
│   ├── background.js         # Service worker handling requests to Python backend
│   ├── content.js            # Content script detecting Netflix card hovers & badges
│   ├── styles.css            # Styling for badges, tooltip cards, and modal integration
│   ├── generate_icons.py     # Script that generated the extension icons
│   ├── icons/                # Extension PNG icons (16, 32, 48, 128)
│   └── popup/
│       ├── popup.html        # Extension toolbar popup interface
│       ├── popup.js          # Status checker and test search logic
│       └── popup.css         # Popup dark-mode styling
│
└── README.md
```

---

## ⚙️ Configuration & Options

### Using an OMDb API Key (Optional)

By default, the backend fetches ratings directly from IMDb without requiring any API key or subscription.

If you have a free or paid **OMDb API key** and prefer to use it:
```bash
export OMDB_API_KEY="your_api_key_here"
python3 server.py
```

---

## 🔧 Troubleshooting

- **Badge shows "Offline ⚠️"**:
  Make sure `python3 server.py` is running in your terminal. You can check the status anytime by clicking the extension icon in Chrome's toolbar.
- **Ratings not appearing immediately**:
  Netflix dynamically loads content as you scroll. A 180ms hover debounce prevents excessive requests during quick mouse sweeps. Keep your cursor on the card for a moment.
- **Port Conflict**:
  If port 5000 is used by AirPlay Receiver on macOS (Monterey/Ventura/Sonoma), you can change `PORT = 5000` to `PORT = 5001` in `server.py` and update `BACKEND_URL` in `background.js`.
