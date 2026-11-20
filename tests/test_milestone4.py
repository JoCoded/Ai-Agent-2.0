import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from creative_agent.integrations import ReadOnlyGateway, ToolAccessError
from creative_agent.knowledge import Asset, KnowledgeStore
from creative_agent.planner import Brief
from creative_agent.supervisor import coordinate


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.store = KnowledgeStore([
            Asset("a", "Studio A", "Portfolio guide", "Present portfolio examples clearly", True, "guide-1"),
            Asset("b", "Studio A", "Portfolio draft", "Portfolio drafting idea", False, "unreviewed"),
            Asset("c", "Studio B", "Portfolio secret", "Private portfolio detail", True, "guide-2"),
        ])

    def test_only_approved_same_brand_results(self):
        records = self.store.retrieve(brand="studio a", query="portfolio")
        self.assertEqual([x["id"] for x in records], ["a"])
        self.assertTrue(all(x["approved"] for x in records))

    def test_no_match_returns_empty_without_cross_brand_leak(self):
        self.assertEqual(self.store.retrieve(brand="Studio A", query="zoology"), [])

    def test_duplicate_asset_id_rejected(self):
        item = Asset("same", "B", "T", "content", True, "S")
        with self.assertRaises(ValueError):
            KnowledgeStore([item, item])

    def test_bounded_retrieval_parameters(self):
        with self.assertRaises(ValueError):
            self.store.retrieve(brand="Studio A", query="portfolio", limit=0)

    def test_local_json_fixture(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "knowledge_demo.json"
        retrieved = KnowledgeStore.from_json(path).retrieve(
            brand="Example Studio", query="portfolio"
        )
        self.assertEqual([x["id"] for x in retrieved], ["demo-portfolio-guidance"])

    def test_unapproved_asset_never_retrieved_from_json(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets.json"
            path.write_text(json.dumps([{"id":"x","brand":"B","title":"Topic",
                "text":"Topic detail", "approved":False,"source":"s"}]))
            self.assertEqual(KnowledgeStore.from_json(path).retrieve(brand="B",query="Topic"), [])


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.brief = Brief("Studio A", "designers", "education", "instagram", "portfolio")

    def test_default_coordinator_does_not_make_api_calls(self):
        campaign = coordinate(self.brief)
        self.assertNotIn("generated", campaign)
        self.assertFalse(campaign["publishable"])
        self.assertEqual(campaign["orchestration"]["status"], "awaiting_human_review")

    def test_generator_called_in_fixed_order_and_validated(self):
        seen = []
        def fake(brief, module, references):
            seen.append((module, len(references)))
            fields = {
                "strategy": ("key_message", "audience_insight", "recommended_angle"),
                "copywriting": ("headline", "caption", "cta"),
                "video_script": ("hook", "voiceover", "visual_direction")
            }[module]
            return {key: f"Draft {key} [VERIFY]" for key in fields}
        store = KnowledgeStore([
            Asset("x", "Studio A", "Portfolio example", "portfolio", True, "local")
        ])
        result = coordinate(self.brief, store=store, generator=fake)
        self.assertEqual([x[0] for x in seen], ["strategy", "copywriting", "video_script"])
        self.assertTrue(all(x[1] == 1 for x in seen))
        self.assertFalse(result["publishable"])
        self.assertTrue(all(not out["publishable"] for out in result["generated"].values()))

    def test_invalid_generated_draft_fails_closed(self):
        with self.assertRaisesRegex(Exception, "schema"):
            coordinate(self.brief, generator=lambda b, m, r: {"headline": "only one"})


class GatewayTests(unittest.TestCase):
    def test_denies_unapproved_access(self):
        gateway = ReadOnlyGateway({"read_assets": lambda args: [args["name"]]})
        with self.assertRaises(ToolAccessError):
            gateway.invoke("read_assets", {"name": "x"})
        self.assertEqual(gateway.invoke("read_assets", {"name": "x"}, consent=True), ["x"])

    def test_denies_unlisted_tool_even_with_consent(self):
        gateway = ReadOnlyGateway({"read_assets": lambda _: []})
        with self.assertRaises(ToolAccessError):
            gateway.invoke("publish_post", {}, consent=True)

    def test_denies_registration_of_write_tool(self):
        with self.assertRaises(ToolAccessError):
            ReadOnlyGateway({"delete_asset": lambda _: None})

    def test_denies_invalid_argument_type(self):
        gateway = ReadOnlyGateway({"read_assets": lambda _: None})
        with self.assertRaises(ToolAccessError):
            gateway.invoke("read_assets", "bad", consent=True)


if __name__ == "__main__":
    unittest.main()
