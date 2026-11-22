"""Loopback-only dashboard: optional explicit provider calls and no publishing.

Run with: python -m creative_agent.dashboard
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import tempfile
from threading import RLock
from urllib.parse import urlsplit

from .knowledge import Asset, KnowledgeStore
from .history import HistoryStore
from .ai_provider import GenerationError, GenerationSettings, FIELDS, generate
from .planner import Brief
from .supervisor import coordinate

HERE = Path(__file__).resolve().parents[1]
UI = HERE / "web" / "index.html"
MAX_BYTES = 12_000
MAX_ASSETS = 250
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,48}$")


class DashboardService:
    def __init__(self, asset_path: Path, history_path: Path | None = None):
        self.asset_path = Path(asset_path)
        self._asset_lock = RLock()
        self.history = HistoryStore(history_path or self.asset_path.with_name("drafts.json"))

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
        with self._asset_lock:
            records = self.load()
            records.append(vars(asset))
            self.save(records)
        return vars(asset)

    def review_asset(self, payload):
        if not isinstance(payload, dict) or type(payload.get("approve")) is not bool:
            raise ValueError("review requires asset id and explicit boolean approve")
        identifier = payload.get("id")
        with self._asset_lock:
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
        campaign = coordinate(brief, store=store)
        row = self.history.add(campaign, kind="offline")
        campaign["draft_id"] = row["id"]
        return campaign

    def history_list(self):
        return self.history.list()

    def review_draft(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"id", "reviewer", "approve", "notes"}:
            raise ValueError("invalid review request")
        return self.history.decide(
            payload.get("id"), reviewer=payload.get("reviewer"),
            approve=payload.get("approve"), notes=payload.get("notes", "")
        )

    def generate_draft(self, payload):
        """Explicit one-module provider call; never send an API key to the browser."""
        if os.environ.get("CREATIVE_AGENT_ENABLE_AI") != "1":
            raise GenerationError("Live AI generation is disabled on this computer")
        if not isinstance(payload, dict) or set(payload) != {"brief", "module", "confirm_cost"}:
            raise ValueError("expected brief, module, and explicit cost confirmation")
        if payload["confirm_cost"] is not True:
            raise ValueError("cost confirmation required")
        module = payload["module"]
        if module not in FIELDS:
            raise ValueError("invalid specialist module")
        # Require an explicit cost estimate and ceiling before any billable request.
        settings = GenerationSettings(
            model=os.environ["CREATIVE_AGENT_MODEL"],
            max_output_tokens=250,
            estimated_input_usd_per_million=float(os.environ["CREATIVE_AGENT_INPUT_USD_PER_MILLION"]),
            estimated_output_usd_per_million=float(os.environ["CREATIVE_AGENT_OUTPUT_USD_PER_MILLION"]),
            max_estimated_request_usd=float(os.environ["CREATIVE_AGENT_REQUEST_CAP_USD"]),
        )
        raw_brief = payload["brief"]
        if not isinstance(raw_brief, dict) or set(raw_brief) - {"brand","audience","goal","platform","topic","tone"}:
            raise ValueError("invalid brief")
        brief = Brief(**raw_brief)
        campaign = coordinate(brief, store=KnowledgeStore([Asset(**a) for a in self.load()]))
        # Provider request is scoped to the brief only: no private reference upload.
        output = generate(brief, module, settings=settings)
        campaign["generated"] = {module: output}
        campaign["limitations"].append("Generated text is unverified. Brand references were not sent to AI.")
        row = self.history.add(campaign, kind="ai")
        campaign["draft_id"] = row["id"]
        return campaign


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

        def _valid_host(self):
            # Protect local/private assets from DNS-rebinding Host spoofing.
            return self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self._valid_host():
                self._json(403, {"error": "Local dashboard only"})
                return
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
            elif path == "/api/history":
                try:
                    self._json(200, {"drafts": service.history_list()})
                except (ValueError, OSError, TypeError, KeyError):
                    self._json(400, {"error": "Could not read draft history"})
            elif path == "/api/config":
                self._json(200, {"ai_enabled": os.environ.get("CREATIVE_AGENT_ENABLE_AI") == "1"})
            elif path == "/api/assets":
                try:
                    self._json(200, {"assets": service.assets()})
                except (ValueError, OSError, TypeError, KeyError) as exc:
                    self._json(400, {"error": "Could not read local assets"})
            else:
                self._json(404, {"error": "Not found"})

        def do_POST(self):
            path = self._path()
            if path not in ("/api/plan", "/api/assets", "/api/review", "/api/generate", "/api/history/review"):
                self._json(404, {"error": "Not found"})
                return
            # Loopback-only plus exact Origin comparison for browser POSTs.
            origin = self.headers.get("Origin")
            authority = self.headers.get("Host", "")
            if not self._valid_host() or origin != f"http://{authority}":
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
                elif path == "/api/review":
                    result = service.review_asset(payload)
                elif path == "/api/history/review":
                    result = service.review_draft(payload)
                else:
                    result = service.generate_draft(payload)
            except GenerationError:
                self._json(400, {"error": "AI generation failed or is disabled. Check local configuration, budget and model."})
                return
            except (ValueError, TypeError, KeyError, UnicodeDecodeError, OSError, OverflowError):
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
    print("Local-only. AI calls require explicit opt-in, configuration and confirmation. No publishing.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
