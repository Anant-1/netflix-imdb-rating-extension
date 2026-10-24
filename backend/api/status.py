"""Vercel serverless health endpoint."""

import json
from http.server import BaseHTTPRequestHandler

from server import OMDB_API_KEY, get_cached_rating_count, init_db, is_supabase_configured


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()

    def do_GET(self):
        init_db()
        cached_count = get_cached_rating_count()
        payload = {
            "status": "online",
            "service": "Netflix IMDb Rating Backend",
            "cached_titles": cached_count,
            "omdb_configured": bool(OMDB_API_KEY),
            "supabase_configured": is_supabase_configured(),
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
