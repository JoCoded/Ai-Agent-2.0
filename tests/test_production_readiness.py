"""Production-readiness regression suite (no API key and no external network)."""
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import os
import unittest
from unittest.mock import patch

from creative_agent.dashboard import DashboardService, make_handler
from creative_agent.history import HistoryStore
from creative_agent.planner import Brief
from creative_agent.supervisor import coordinate


BRIEF = dict(brand="Demo Brand", audience="young engineers", goal="education",
             platform="linkedin", topic="electric vehicles")


class ConcurrentStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.service = DashboardService(root / "assets.json")
        self.store = self.service.history

    def test_simultaneous_asset_creation_preserves_every_entry(self):
        def add(i):
            return self.service.add_asset({
                "id": f"asset-{i}", "brand": "Demo Brand",
                "title": f"Guide {i}", "text": "Electric vehicles",
                "source": "Fictional sample",
            })
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(add, range(25)))
        assets = self.service.assets()
        self.assertEqual(len(assets), 25)
        self.assertTrue(all(row["approved"] is False for row in assets))

    def test_simultaneous_draft_creation_preserves_every_entry(self):
        brief = Brief(**BRIEF)
        def create(i):
            return self.store.add(coordinate(brief), kind="offline")
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(create, range(25)))
        saved = self.store.list()
        self.assertEqual(len(saved), 25)
        self.assertEqual(len(set(row["id"] for row in saved)), 25)

    def test_competing_review_decisions_cannot_both_succeed(self):
        brief = Brief(**BRIEF)
        row = self.store.add(coordinate(brief), kind="offline")
        def review(choice):
            try:
                self.store.decide(row["id"], reviewer="Editor", approve=choice)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(review, [True, False]))
        self.assertEqual(sum(outcomes), 1)
        self.assertFalse(self.store.list()[0]["campaign"]["publishable"])

    def test_duplicate_identifiers_under_contention_rejected(self):
        def add(_):
            try:
                self.service.add_asset({
                    "id": "only-one", "brand": "Demo Brand",
                    "title": "Guide", "text": "Electric vehicles",
                    "source": "Fictional sample",
                })
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(add, range(12)))
        self.assertEqual(sum(outcomes), 1)
        self.assertEqual(len(self.service.assets()), 1)


class FullHTTPWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = DashboardService(Path(self.tmp.name) / "assets.json")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        self.addCleanup(self.server.server_close)
        thread = Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def call(self, path, method="GET", payload=None, *, origin=True, host=None):
        headers = {}
        if host is not None:
            headers["Host"] = host
        if method == "POST":
            headers["Content-Type"] = "application/json"
            if origin:
                headers["Origin"] = self.base
        request = Request(
            self.base + path, method=method, headers=headers,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        with urlopen(request, timeout=5) as response:
            return response.status, json.load(response) if path != "/" else response.read()

    def test_complete_reference_draft_review_roundtrip(self):
        status, asset = self.call("/api/assets", "POST", dict(
            id="ev-guide", brand="Demo Brand", title="Electric vehicle guide",
            text="Explain electric vehicle principles with verified examples.",
            source="Fictional guide",
        ))
        self.assertEqual(status, 200)
        self.assertFalse(asset["approved"])
        _, first = self.call("/api/plan", "POST", BRIEF)
        self.assertEqual(first["retrieval"]["references"], [])
        self.call("/api/review", "POST", {"id": "ev-guide", "approve": True})
        _, second = self.call("/api/plan", "POST", BRIEF)
        self.assertEqual([r["id"] for r in second["retrieval"]["references"]], ["ev-guide"])
        self.assertFalse(second["publishable"])
        _, saved = self.call("/api/history")
        self.assertEqual(len(saved["drafts"]), 2)
        _, reviewed = self.call("/api/history/review", "POST", {
            "id": second["draft_id"], "reviewer": "Human Editor",
            "approve": True, "notes": "Demo review; verify all assertions.",
        })
        self.assertEqual(reviewed["review"]["state"], "approved")
        self.assertFalse(reviewed["campaign"]["publishable"])
        _, persisted = self.call("/api/history")
        self.assertEqual(persisted["drafts"][0]["review"]["state"], "approved")

    def test_malicious_host_header_blocked_on_private_reads(self):
        request = Request(self.base + "/api/history", headers={"Host": "malicious.test"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 403)

    def test_live_generation_requires_opt_in(self):
        with patch.dict(os.environ, {"CREATIVE_AGENT_ENABLE_AI": "0"}):
            with self.assertRaises(HTTPError) as ctx:
                self.call("/api/generate", "POST", {
                    "brief": BRIEF, "module": "copywriting", "confirm_cost": True,
                })
        self.assertEqual(ctx.exception.code, 400)
        self.assertEqual(self.service.history_list(), [])

    def test_api_cannot_accept_cross_origin_write(self):
        request = Request(
            self.base + "/api/plan", method="POST",
            headers={"Origin": "http://attacker.test", "Content-Type": "application/json"},
            data=json.dumps(BRIEF).encode(),
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 403)

    def test_dashboard_html_uses_no_external_scripts(self):
        request = Request(self.base + "/")
        with urlopen(request, timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn("Creative Agent", html)
        self.assertNotIn("https://cdn.", html)
        self.assertIn('id="aiGenerate"', html)
        self.assertIn('id="history"', html)


if __name__ == "__main__":
    unittest.main()
