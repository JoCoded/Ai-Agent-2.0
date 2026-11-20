import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from creative_agent.dashboard import DashboardService, make_handler


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = DashboardService(Path(self.tmp.name) / "assets.json")

    def test_create_requires_review(self):
        asset = self.service.add_asset(dict(
            id="guide-1",brand="Demo",title="Palette",text="Use warm amber",
            source="Brand document"))
        self.assertFalse(asset["approved"])
        self.assertFalse(self.service.assets()[0]["approved"])

    def test_reject_self_approval(self):
        with self.assertRaises(ValueError):
            self.service.add_asset(dict(id="a",brand="B",title="T",text="Text",
                                        source="S",approved=True))

    def test_review_controls_retrieval(self):
        self.service.add_asset(dict(id="a",brand="Demo",title="Palette",text="Warm amber palette",source="G"))
        brief=dict(brand="Demo",audience="designers",goal="education",
                   platform="instagram",topic="palette")
        self.assertEqual(self.service.plan(brief)["retrieval"]["references"], [])
        self.service.review_asset({"id":"a","approve":True})
        self.assertEqual(len(self.service.plan(brief)["retrieval"]["references"]),1)
        self.service.review_asset({"id":"a","approve":False})
        self.assertEqual(self.service.plan(brief)["retrieval"]["references"], [])

    def test_duplicate_id_refused(self):
        record=dict(id="a",brand="B",title="T",text="Text",source="S")
        self.service.add_asset(record)
        with self.assertRaises(ValueError):
            self.service.add_asset(record)

    def test_reject_unknown_brief_fields(self):
        with self.assertRaises(ValueError):
            self.service.plan(dict(brand="B", audience="A",goal="education",
                                   platform="x",topic="topic", secret="ignored"))

    def test_no_cross_brand_references(self):
        self.service.add_asset(dict(id="x",brand="Other",title="Portfolio",text="Portfolio facts",source="S"))
        self.service.review_asset({"id":"x","approve":True})
        out=self.service.plan(dict(brand="Demo",audience="designers",goal="education",
                                   platform="x",topic="portfolio"))
        self.assertEqual(out["retrieval"]["references"],[])
        self.assertFalse(out["publishable"])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(
            DashboardService(Path(self.tmp.name)/"local.json")))
        self.addCleanup(server.server_close)
        self.server=server
        t=threading.Thread(target=server.serve_forever,daemon=True)
        t.start()
        self.addCleanup(server.shutdown)
        self.base=f"http://127.0.0.1:{server.server_address[1]}"

    def call(self,path,method="GET",body=None,origin=True):
        hdr={"Content-Type":"application/json"} if method=="POST" else {}
        if method=="POST" and origin:hdr["Origin"]=self.base
        request=Request(self.base+path,method=method,headers=hdr,
                        data=json.dumps(body).encode() if body is not None else None)
        return urlopen(request,timeout=3)

    def test_dashboard_html_served_locally(self):
        with self.call("/") as response:
            self.assertEqual(response.status,200)
            self.assertIn(b"Creative Agent Studio",response.read())

    def test_get_assets_empty(self):
        with self.call("/api/assets") as response:
            self.assertEqual(json.load(response),{"assets":[]})

    def test_plan_endpoint_never_approves(self):
        brief=dict(brand="Demo",audience="engineers",goal="education",
                   platform="instagram",topic="battery health")
        with self.call("/api/plan","POST",brief) as response:
            data=json.load(response)
        self.assertEqual(data["review"]["state"],"needs_review")
        self.assertFalse(data["publishable"])

    def test_cross_origin_post_rejected(self):
        with self.assertRaises(HTTPError) as ctx:
            self.call("/api/plan","POST",{"brand":"Demo"},origin=False)
        self.assertEqual(ctx.exception.code,403)

    def test_unknown_route_not_exposed(self):
        with self.assertRaises(HTTPError) as ctx:
            self.call("/../private","GET")
        self.assertEqual(ctx.exception.code,404)


if __name__=="__main__":
    unittest.main()
