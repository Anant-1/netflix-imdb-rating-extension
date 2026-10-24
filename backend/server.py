#!/usr/bin/env python3
"""
Netflix IMDb Rating Backend Server
Zero external dependencies required (uses standard library http.server and urllib).
Optionally supports OMDB_API_KEY if configured in environment or .env file.
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Paths & Settings
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
HOST = "127.0.0.1"
PORT = 5000

def get_omdb_key():
    """Load OMDB_API_KEY from config.json or environment variable."""
    key = os.environ.get("OMDB_API_KEY", "").strip()
    if not key and CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                key = cfg.get("omdb_api_key", "").strip()
        except Exception:
            pass
    return key

OMDB_API_KEY = get_omdb_key()

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


# --- Supabase Cache ---
def is_supabase_configured():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def init_db():
    """Ensure the server has Supabase credentials; schema is managed in Supabase."""
    if not is_supabase_configured():
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")


def _supabase_request(method, path, payload=None, prefer=None, range_header=None):
    if not is_supabase_configured():
        raise RuntimeError("Supabase is not configured")

    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("apikey", SUPABASE_SERVICE_ROLE_KEY)
    request.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_ROLE_KEY}")
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if prefer:
        request.add_header("Prefer", prefer)
    if range_header:
        request.add_header("Range", range_header)

    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read(), response.headers


def get_cached_rating(query_title):
    try:
        params = urllib.parse.urlencode({
            "select": "title,imdb_id,rating,votes,year,genre,plot,source,updated_at",
            "query_title": f"eq.{query_title.lower().strip()}",
            "limit": "1",
        })
        body, _ = _supabase_request("GET", f"ratings?{params}")
        rows = json.loads(body.decode("utf-8"))
        if rows:
            row = rows[0]
            # Cache valid for 30 days
            if time.time() - int(row.get("updated_at") or 0) < 30 * 86400:
                return {
                    "title": row.get("title", ""),
                    "imdb_id": row.get("imdb_id", ""),
                    "rating": row.get("rating", "N/A"),
                    "votes": row.get("votes", "N/A"),
                    "year": row.get("year", "N/A"),
                    "genre": row.get("genre", ""),
                    "plot": row.get("plot", ""),
                    "source": row.get("source", "IMDb"),
                    "cached": True,
                }
    except Exception as e:
        print(f"[Cache Error] {e}")
    return None


def save_cached_rating(query_title, data):
    try:
        payload = {
            "query_title": query_title.lower().strip(),
            "title": data.get("title", ""),
            "imdb_id": data.get("imdb_id", ""),
            "rating": data.get("rating", "N/A"),
            "votes": data.get("votes", "N/A"),
            "year": data.get("year", "N/A"),
            "genre": data.get("genre", ""),
            "plot": data.get("plot", ""),
            "source": data.get("source", "IMDb"),
            "updated_at": int(time.time()),
        }
        path = "ratings?on_conflict=query_title"
        _supabase_request(
            "POST",
            path,
            payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )
    except Exception as e:
        print(f"[Cache Save Error] {e}")


def get_cached_rating_count():
    """Return the number of cache rows, or 0 when Supabase is unavailable."""
    try:
        body, headers = _supabase_request(
            "GET",
            "ratings?select=query_title",
            prefer="count=exact",
            range_header="0-0",
        )
        content_range = headers.get("Content-Range", "")
        total = content_range.rsplit("/", 1)[-1]
        return int(total) if total.isdigit() else len(json.loads(body.decode("utf-8")))
    except Exception as e:
        print(f"[Cache Count Error] {e}")
        return 0


# --- Rating Fetchers ---

def fetch_from_omdb(title, api_key):
    """Fetch rating using OMDb API if user has a key."""
    if not api_key:
        return None
    try:
        query_encoded = urllib.parse.quote(title)
        url = f"https://www.omdbapi.com/?t={query_encoded}&apikey={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("Response") == "True":
                return {
                    "title": res_data.get("Title", title),
                    "imdb_id": res_data.get("imdbID", ""),
                    "rating": res_data.get("imdbRating", "N/A"),
                    "votes": res_data.get("imdbVotes", "N/A"),
                    "year": res_data.get("Year", "N/A"),
                    "genre": res_data.get("Genre", "N/A"),
                    "plot": res_data.get("Plot", ""),
                    "source": "OMDb",
                }
    except Exception as e:
        print(f"[OMDb fetch error] {e}")
    return None


def fetch_from_imdb_direct(title):
    """
    Fetch IMDb rating directly without requiring an API key.
    1. Uses IMDb's suggestion API to find the title ID (tt...).
    2. Uses a clean web reader proxy to bypass IMDb's AWS WAF anti-bot challenge (HTTP 202).
    3. Extracts rating, vote count, year, genre, and plot summary.
    """
    # 1. Clean title for suggestion API slug
    clean_title = re.sub(r"[^\w\s-]", "", title).strip().lower()
    slug = re.sub(r"[\s_]+", "_", clean_title)
    if not slug:
        slug = urllib.parse.quote(title)

    suggest_url = f"https://v3.sg.media-imdb.com/suggestion/x/{slug}.json"
    imdb_id = None
    suggested_title = title
    suggested_year = "N/A"

    try:
        req = urllib.request.Request(
            suggest_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            sdata = json.loads(response.read().decode("utf-8"))
            items = sdata.get("d", [])
            for item in items:
                iid = item.get("id", "")
                if iid.startswith("tt"):
                    imdb_id = iid
                    suggested_title = item.get("l", title)
                    suggested_year = str(item.get("y", item.get("yr", "N/A")))
                    break
    except Exception as e:
        print(f"[IMDb suggestion error for '{title}']: {e}")

    if not imdb_id:
        return None

    # 2. Fetch page content bypassing AWS WAF
    rating = "N/A"
    votes = "N/A"
    genre = "N/A"
    plot = ""

    # Strategy A: Use Reader proxy to bypass IMDb's AWS WAF 202 JS challenge
    try:
        reader_url = f"https://r.jina.ai/https://www.imdb.com/title/{imdb_id}/"
        rreq = urllib.request.Request(reader_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(rreq, timeout=8) as r:
            text = r.read().decode("utf-8", errors="ignore")

            # Extract Rating & Votes (e.g. "8.8/10 2.9M" or "★ 8.8")
            rv_match = re.search(r"([0-9\.]+)\s*/\s*10\s+([0-9\.,]+[KkMm]?)", text)
            if rv_match:
                rating = rv_match.group(1)
                votes = rv_match.group(2)
            else:
                star_match = re.search(r"[⭐★]\s*([0-9\.]+)", text)
                if star_match:
                    rating = star_match.group(1)

            # Extract Genre from Title header line: "Title: Inception (2010) ⭐ 8.8 | Adventure, Sci-Fi..."
            first_line = text.split("\n")[0]
            if "|" in first_line:
                genre = first_line.split("|")[-1].strip()

            # Extract Plot summary
            plot_match = re.search(r"(?:Plot|Summary|Storyline)[^\n]*\n+([A-Z][^\n]{50,400}\.)", text)
            if plot_match:
                plot = plot_match.group(1).strip()
            else:
                # Fallback to finding description paragraph
                desc_match = re.search(r"\n([A-Z][^\n]{60,300}\.)\n", text)
                if desc_match:
                    plot = desc_match.group(1).strip()

            if rating != "N/A":
                return {
                    "title": suggested_title,
                    "imdb_id": imdb_id,
                    "rating": rating,
                    "votes": votes,
                    "year": suggested_year,
                    "genre": genre,
                    "plot": plot,
                    "source": "IMDb",
                }
    except Exception as e:
        print(f"[IMDb reader fetch error for '{imdb_id}']: {e}")

    # Strategy B: Direct fetch fallback
    try:
        page_url = f"https://www.imdb.com/title/{imdb_id}/"
        preq = urllib.request.Request(page_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(preq, timeout=6) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
            ld_match = re.search(r'<script type="application/ld\+json">({.*?})</script>', page_html, re.DOTALL)
            if ld_match:
                ld_data = json.loads(ld_match.group(1))
                agg = ld_data.get("aggregateRating", {})
                if agg:
                    rating = str(agg.get("ratingValue", "N/A"))
                    rc = agg.get("ratingCount")
                    if rc:
                        votes = format_vote_count(rc)
                if "genre" in ld_data:
                    g = ld_data["genre"]
                    genre = ", ".join(g) if isinstance(g, list) else str(g)
                if "description" in ld_data:
                    plot = html.unescape(ld_data["description"])
    except Exception as e:
        print(f"[IMDb direct HTML fallback error for '{imdb_id}']: {e}")

    if imdb_id:
        return {
            "title": suggested_title,
            "imdb_id": imdb_id,
            "rating": rating,
            "votes": votes,
            "year": suggested_year,
            "genre": genre,
            "plot": plot,
            "source": "IMDb",
        }

    return None


def format_vote_count(count):
    """Format vote count into readable K/M suffix."""
    try:
        val = int(count)
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val / 1_000:.0f}K"
        return str(val)
    except Exception:
        return str(count)


def lookup_movie(title):
    """Full lookup workflow with caching and multi-strategy fetching."""
    cleaned = title.strip()
    if not cleaned:
        return None

    # Check cache first
    cached = get_cached_rating(cleaned)
    if cached:
        return cached

    # Strategy 1: OMDb if API key is provided
    result = None
    if OMDB_API_KEY:
        print('Using omdb')
        result = fetch_from_omdb(cleaned, OMDB_API_KEY)

    # Strategy 2: Direct IMDb scraping
    if not result:
        print('using imdb')
        result = fetch_from_imdb_direct(cleaned)

    # Cache if found
    if result:
        result["cached"] = False
        save_cached_rating(cleaned, result)
        return result

    return None


# --- HTTP Server Handler ---

class RatingHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/rating":
            title = params.get("title", [""])[0].strip()
            if not title:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Missing 'title' parameter"}).encode())
                return

            print(f"🔍 [Lookup Request] '{title}'...")
            res = lookup_movie(title)
            try:
                if res:
                    print(f"⭐ [Found] {res.get('title')} ({res.get('year')}) -> IMDb: {res.get('rating')}/10 (cached: {res.get('cached')})")
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {"success": True, **res}
                    self.wfile.write(json.dumps(payload).encode())
                else:
                    print(f"❌ [Not Found] '{title}'")
                    self.send_response(404)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {"success": False, "error": "Movie not found", "title": title}
                    self.wfile.write(json.dumps(payload).encode())
            except (BrokenPipeError, ConnectionResetError):
                # Browser aborted the request before the response could be delivered
                print(f"⚡ [Client Closed Connection] '{title}' (hover moved away)")

        elif path == "/status":
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            cached_count = get_cached_rating_count()

            status_payload = {
                "status": "online",
                "service": "Netflix IMDb Rating Backend",
                "cached_titles": cached_count,
                "omdb_configured": bool(OMDB_API_KEY),
                "supabase_configured": is_supabase_configured(),
            }
            self.wfile.write(json.dumps(status_payload).encode())

        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

    def log_message(self, format, *args):
        # Override standard log to keep terminal output clean
        return


def run_server():
    init_db()
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, RatingHandler)
    print("=" * 60)
    print("🎬 Netflix IMDb Rating Backend Server")
    print("=" * 60)
    print(f"🚀 Running at: http://{HOST}:{PORT}")
    print(f"📡 Ready to accept requests from Chrome Extension")
    print(f"📦 Cache: Supabase ({SUPABASE_URL})")
    if OMDB_API_KEY:
        print("🔑 OMDb API Key: Configured")
    else:
        print("🌐 Mode: Direct IMDb Scraping & Suggestion API (Free, no key needed)")
    print("=" * 60)
    print("Press Ctrl+C to stop the server\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server gracefully...")
        httpd.server_close()
        sys.exit(0)


if __name__ == "__main__":
    run_server()
