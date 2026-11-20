"""Local-only dashboard server: no credentials, external API calls, or publishing.

Run with: python -m creative_agent.dashboard
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import tempfile
from urllib.parse import urlsplit

from .knowledge import Asset, KnowledgeStore
from .planner import Brief
from .supervisor import coordinate

HERE = Path(__file__).resolve().parents[1]
UI = HERE / "web" / "index.html"
MAX_BYTES = 12_000
MAX_ASSETS = 250
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,48}$")


class DashboardService:
    def __init__(self, asset_path: Path):
        self.asset_path = Path(asset_path)

    def load(self):
        if not self.asset_path.exists():
            return []
        if self.asset_path.stat().st_size > 1_000_000:
            raise ValueError("local asset file exceeds size limit")
        records = json.loads(self.asset_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("local asset file must be a JSON array")
        # Validate entries, including explicit review flags and unique IDs.
        KnowledgeStore([Asset(**row) for row in records])
        return records

    def save(self, records):
        if len(records) > MAX_ASSETS:
            raise ValueError("too many local assets")
        KnowledgeStore([Asset(**row) for row in records])
        self.asset_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.asset_path.parent, prefix=".assets-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(records, handle, indent=2)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.asset_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def assets(self):
        return self.load()

    def add_asset(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("expected asset object")
        if payload.get("approved") is not None:
            raise ValueError("new assets cannot self-approve")
        if not SAFE_ID.fullmatch(str(payload.get("id", ""))):
            raise ValueError("asset id must contain only letters, digits, _ or -")
        asset = Asset(
            id=payload["id"], brand=payload.get("brand"),
            title=payload.get("title"), text=payload.get("text"),
            source=payload.get("source"), approved=False,
        )
        records = self.load()
        records.append(vars(asset))
        self.save(records)
        return vars(asset)

    def review_asset(self, payload):
        if not isinstance(payload, dict) or type(payload.get("approve")) is not bool:
            raise ValueError("review requires asset id and explicit boolean approve")
        identifier = payload.get("id")
        records = self.load()
        for row in records:
            if row["id"] == identifier:
                row["approved"] = payload["approve"]
                self.save(records)
                return row
        raise ValueError("asset not found")

    def plan(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("expected a brief object")
        # Do not accept unexpected fields or arbitrary server paths.
        fields = {"brand", "audience", "goal", "platform", "topic", "tone"}
        if set(payload) - fields:
            raise ValueError("unexpected brief fields")
        brief = Brief(**payload)
        store = KnowledgeStore([Asset(**item) for item in self.load()])
        return coordinate(brief, store=store)


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status, data):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _path(self):
            return urlsplit(self.path).path

        def do_GET(self):
            path = self._path()
            if path == "/":
                body = UI.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/assets":
                try:
                    self._json(200, {"assets": service.assets()})
                except (ValueError, OSError, TypeError, KeyError) as exc:
                    self._json(400, {"error": "Could not read local assets"})
            else:
                self._json(404, {"error": "Not found"})

        def do_POST(self):
            path = self._path()
            if path not in ("/api/plan", "/api/assets", "/api/review"):
                self._json(404, {"error": "Not found"})
                return
            # Loopback-only plus exact Origin comparison for browser POSTs.
            origin = self.headers.get("Origin")
            authority = self.headers.get("Host", "")
            if origin != f"http://{authority}" or not authority.startswith("127.0.0.1:"):
                self._json(403, {"error": "Only requests from the local dashboard are allowed"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                self._json(415, {"error": "Expected application/json"})
                return
            try:
                count = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._json(400, {"error": "Invalid content length"})
                return
            if not 0 < count <= MAX_BYTES:
                self._json(413, {"error": "Payload too large or empty"})
                return
            try:
                payload = json.loads(self.rfile.read(count).decode("utf-8"))
                if path == "/api/plan":
                    result = service.plan(payload)
                elif path == "/api/assets":
                    result = service.add_asset(payload)
                else:
                    result = service.review_asset(payload)
            except (ValueError, TypeError, KeyError, UnicodeDecodeError, OSError):
                self._json(400, {"error": "Invalid or incomplete input"})
                return
            self._json(200, result)

        def log_message(self, format, *args):
            # Avoid logging user-provided content or private brand information.
            pass
    return Handler


def main():
    path = Path(os.environ.get("CREATIVE_AGENT_ASSETS_FILE",
                               str(Path.home() / ".creative-agent" / "assets.json")))
    server = ThreadingHTTPServer(("127.0.0.1", 8765), make_handler(DashboardService(path)))
    print("Creative Agent dashboard: http://127.0.0.1:8765")
    print("Local-only; no AI API calls or publishing. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
