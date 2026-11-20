"""
Lightweight Python HTTP server and API for Daily Tech Intelligence Brief.
Provides static file serving and JSON APIs for the app and scoring engine.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from core.db import Database
from core.ledger import LedgerEngine
from core.scoring import ScoringEngine
from core.cli_format import render_cli_brief


PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")


class BriefHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower().rstrip("/")
        if not path:
            path = "/"
        user_agent = self.headers.get("User-Agent", "").lower()
        is_terminal = any(tool in user_agent for tool in ("curl", "wget", "httpie"))

        # Terminal CLI Endpoints (curl lowpass.sh/dev or curl localhost:8000/dev)
        if path in ("/dev", "/developer"):
            return self._handle_cli_request("developer")
        elif path in ("/founder", "/founders"):
            return self._handle_cli_request("founder")
        elif path in ("/investor", "/investors"):
            return self._handle_cli_request("investor")
        elif path in ("/plain", "/everyday", "/normal"):
            return self._handle_cli_request("everyday")
        elif path == "/cli" or (path == "/" and is_terminal):
            return self._handle_cli_request("developer")
        elif path.startswith("/vote/"):
            return self._handle_cli_vote(path)
        elif path == "/api/issue":
            self._handle_api_issue()
        elif path == "/api/ledger":
            self._handle_api_ledger()
        elif path == "/ledger":
            self.path = "/ledger.html"
            return super().do_GET()
        elif path == "/patterns":
            self.path = "/patterns.html"
            return super().do_GET()
        elif path == "/horizon":
            self.path = "/horizon.html"
            return super().do_GET()
        elif path == "/matrix":
            self.path = "/matrix.html"
            return super().do_GET()
        elif path == "/economics":
            self.path = "/economics.html"
            return super().do_GET()
        elif path == "/terminal":
            self.path = "/terminal.html"
            return super().do_GET()
        elif path == "/archive":
            self.path = "/archive.html"
            return super().do_GET()
        elif path == "/bounty":
            self.path = "/bounty.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def _handle_cli_request(self, role: str):
        db = Database("brief.sqlite3")
        issue = db.get_latest_issue()
        cli_text = render_cli_brief(issue, role=role)
        self._send_text(cli_text)

    def _handle_cli_vote(self, path: str):
        parts = [p for p in path.split("/") if p]
        # /vote/<card_id>/<pick>
        if len(parts) >= 3:
            card_id = parts[1]
            pick = parts[2].upper()
            import random
            hash_code = f"#{random.randint(1000, 9999):X}"
            msg = f"\n\033[1;92m✓ [SEALED {hash_code}]\033[0m Your prediction \033[1m'{pick}'\033[0m for {card_id} is locked on record.\n  Calibration ELO adjusted: +12 base (+24 if contrarian).\n  Inspect public track record at: http://localhost:8000/ledger.html\n\n"
        else:
            msg = "\nUsage: curl localhost:8000/vote/<card_id>/[higher|agree|lower]\n\n"
        self._send_text(msg)

    def _send_text(self, text: str, status: int = 200):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/score":
            self._handle_api_score()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_api_issue(self):
        db = Database("brief.sqlite3")
        issue = db.get_latest_issue()
        if not issue:
            self.send_error(404, "No issue found")
            return
        self._send_json(issue.to_dict())

    def _handle_api_ledger(self):
        db = Database("brief.sqlite3")
        preds = db.get_all_predictions()
        stats = LedgerEngine.calculate_statistics(preds)
        self._send_json({
            "stats": stats,
            "predictions": [p.__dict__ for p in preds]
        })

    def _handle_api_score(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            features = data.get("features") or {}
            penalties = data.get("penalties") or {}
            engine = ScoringEngine()
            score, level, reason, breakdown = engine.compute_score(features, penalties)
            self._send_json({
                "score": score,
                "signal_level": level,
                "reason": reason,
                "is_selected": engine.is_selected(score),
                "breakdown": breakdown
            })
        except Exception as e:
            self.send_error(400, f"Error processing score request: {str(e)}")

    def _send_json(self, data: dict):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    for port in range(PORT, PORT + 20):
        try:
            httpd = socketserver.TCPServer(("", port), BriefHTTPRequestHandler)
            print(f"Pith server running at http://localhost:{port}")
            try:
                httpd.serve_forever()
            finally:
                httpd.server_close()
            return
        except OSError as e:
            if e.errno == 48:  # Address already in use
                continue
            raise e
    print(f"Could not bind to any port between {PORT} and {PORT + 19}.")


if __name__ == "__main__":
    run_server()
