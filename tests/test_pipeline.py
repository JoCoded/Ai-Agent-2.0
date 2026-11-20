import json
import unittest

from creative_agent.pipeline import (
    Review, copywriting, create_campaign, request_review_decision,
    strategy, video_script,
)
from creative_agent.planner import Brief


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.brief = Brief(
            brand="Demo Brand",
            audience="young engineers",
            goal="education",
            platform="instagram",
            topic="electric vehicle fundamentals",
            tone="clear, relatable",
        )

    def test_strategy_has_pillars_and_measures(self):
        result = strategy(self.brief)
        self.assertEqual(result["module"], "content_strategist")
        self.assertEqual(len(result["content_pillars"]), 3)
        self.assertIn("completion rate", result["success_metrics"])

    def test_copy_contains_placeholder_instead_of_fake_claims(self):
        result = copywriting(self.brief)
        self.assertIn("[add a sourced insight", result["caption"])
        self.assertEqual(result["status"], "draft")

    def test_video_timeline_covers_30_seconds_without_gaps(self):
        result = video_script(self.brief)
        scenes = result["scenes"]
        self.assertEqual(scenes[0]["start"], 0)
        self.assertEqual(scenes[-1]["end"], result["target_duration_seconds"])
        for earlier, later in zip(scenes, scenes[1:]):
            self.assertEqual(earlier["end"], later["start"])

    def test_campaign_defaults_to_review_and_not_publishable(self):
        result = create_campaign(self.brief)
        self.assertEqual(result["review"]["state"], "needs_review")
        self.assertFalse(result["publishable"])
        self.assertIn("copywriting", result)
        self.assertIn("video_script", result)
        self.assertEqual(result, json.loads(json.dumps(result)))

    def test_human_approval_is_recorded_but_not_auto_published(self):
        result = request_review_decision(
            create_campaign(self.brief), reviewer="Human Editor", approve=True
        )
        self.assertEqual(result["review"]["state"], "approved")
        self.assertEqual(result["review"]["reviewer"], "Human Editor")
        self.assertTrue(result["review"]["reviewed_at"])
        self.assertFalse(result["publishable"])

    def test_rejection_creates_changes_requested(self):
        result = request_review_decision(
            create_campaign(self.brief), reviewer="Reviewer", approve=False,
            notes="Replace placeholders and check the claims."
        )
        self.assertEqual(result["review"]["state"], "changes_requested")

    def test_cannot_self_approve_from_pending_defaults(self):
        with self.assertRaises(ValueError):
            Review(state="approved")
        with self.assertRaises(ValueError):
            request_review_decision(create_campaign(self.brief), reviewer=" ", approve=True)

    def test_repeated_decisions_not_allowed(self):
        campaign = request_review_decision(
            create_campaign(self.brief), reviewer="Editor", approve=True
        )
        with self.assertRaises(ValueError):
            request_review_decision(campaign, reviewer="Other", approve=True)

    def test_invalid_payload_rejected(self):
        with self.assertRaises(ValueError):
            request_review_decision({}, reviewer="Editor", approve=True)


if __name__ == "__main__":
    unittest.main()
