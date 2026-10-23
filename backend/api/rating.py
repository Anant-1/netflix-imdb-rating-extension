"""Vercel serverless endpoint for IMDb rating lookups."""

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import init_db, lookup_movie


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        title = params.get("title", [""])[0].strip()
        if not title:
            self._send_json(400, {"success": False, "error": "Missing 'title' parameter"})
            return
        if len(title) > 200:
            self._send_json(400, {"success": False, "error": "Title is too long"})
            return

        init_db()
        result = lookup_movie(title)
        if result:
            self._send_json(200, {"success": True, **result})
        else:
            self._send_json(404, {"success": False, "error": "Movie not found", "title": title})

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
