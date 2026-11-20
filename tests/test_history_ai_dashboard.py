"""Milestone 6: safe offline tests for history, reviewer decisions and AI opt-in."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from creative_agent.dashboard import DashboardService
from creative_agent.history import HistoryStore
from creative_agent.ai_provider import GenerationError
from creative_agent.planner import Brief
from creative_agent.supervisor import coordinate


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = HistoryStore(Path(self.temp.name) / "drafts.json")
        self.brief = Brief("Demo", "students", "education", "instagram", "study skills")

    def create(self):
        return self.store.add(coordinate(self.brief), kind="offline")

    def test_add_and_reload(self):
        row = self.create()
        self.assertEqual(HistoryStore(self.store.path).list()[0]["id"], row["id"])
        self.assertFalse(row["campaign"]["publishable"])

    def test_explicit_approval_stays_unpublishable(self):
        row = self.create()
        revised = self.store.decide(row["id"], reviewer="Editor", approve=True)
        self.assertEqual(revised["review"]["state"], "approved")
        self.assertFalse(revised["campaign"]["publishable"])
        self.assertEqual(self.store.list()[0]["review"]["reviewer"], "Editor")

    def test_rejected_draft_recorded(self):
        row = self.create()
        revised = self.store.decide(row["id"], reviewer="Editor", approve=False, notes="Revise")
        self.assertEqual(revised["review"]["state"], "changes_requested")

    def test_reapproval_rejected(self):
        row = self.create()
        self.store.decide(row["id"], reviewer="Editor", approve=False)
        with self.assertRaises(ValueError):
            self.store.decide(row["id"], reviewer="Editor", approve=True)

    def test_review_requires_real_name(self):
        row = self.create()
        with self.assertRaises(ValueError):
            self.store.decide(row["id"], reviewer="   ", approve=True)

    def test_strict_boolean_for_approval(self):
        row = self.create()
        with self.assertRaises(ValueError):
            self.store.decide(row["id"], reviewer="Editor", approve="yes")

    def test_unpublishable_only(self):
        with self.assertRaises(ValueError):
            self.store.add({"brief": {}, "publishable": True}, kind="offline")

    def test_capacity_limit(self):
        self.store.MAX_ENTRIES = 1
        self.create()
        with self.assertRaises(ValueError):
            self.create()


class DashboardAIGates(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.service = DashboardService(root / "assets.json")
        self.brief = {
            "brand": "Demo", "audience": "students",
            "goal": "education", "platform": "instagram", "topic": "study skills",
        }

    def test_plan_creates_saved_history(self):
        result = self.service.plan(self.brief)
        self.assertTrue(result["draft_id"])
        self.assertEqual(self.service.history_list()[0]["kind"], "offline")

    def test_live_ai_disabled_by_default(self):
        with patch.dict(os.environ, {"CREATIVE_AGENT_ENABLE_AI": "0"}):
            with self.assertRaises(GenerationError):
                self.service.generate_draft({"brief": self.brief, "module": "strategy", "confirm_cost": True})

    def test_ai_requires_confirmed_cost(self):
        with patch.dict(os.environ, {"CREATIVE_AGENT_ENABLE_AI": "1"}):
            with self.assertRaises(ValueError):
                self.service.generate_draft({"brief": self.brief, "module": "strategy", "confirm_cost": False})

    def test_unknown_module_rejected_before_provider(self):
        with patch.dict(os.environ, {"CREATIVE_AGENT_ENABLE_AI": "1"}):
            with self.assertRaises(ValueError):
                self.service.generate_draft({"brief": self.brief, "module": "publish", "confirm_cost": True})

    def test_missing_env_configuration_cannot_call_model(self):
        with patch.dict(os.environ, {"CREATIVE_AGENT_ENABLE_AI": "1"}, clear=True):
            with self.assertRaises(KeyError):
                self.service.generate_draft({"brief": self.brief, "module": "copywriting", "confirm_cost": True})

    def test_review_persists_across_service_instances(self):
        result = self.service.plan(self.brief)
        decision = self.service.review_draft({
            "id": result["draft_id"], "reviewer": "Editor", "approve": True,
        })
        self.assertEqual(decision["review"]["state"], "approved")
        reloaded = DashboardService(self.service.asset_path)
        self.assertEqual(reloaded.history_list()[0]["review"]["state"], "approved")
        self.assertFalse(reloaded.history_list()[0]["campaign"]["publishable"])


if __name__ == "__main__":
    unittest.main()
