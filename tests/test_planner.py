import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative_agent import Brief, create_plan


class CreativePlannerTests(unittest.TestCase):
    def setUp(self):
        self.brief = Brief(
            brand="Example Studio",
            audience="early-career designers",
            goal="education",
            platform="instagram",
            topic="portfolio building",
        )

    def test_reproducible_plan(self):
        self.assertEqual(create_plan(self.brief), create_plan(self.brief))

    def test_platform_specific_formats(self):
        plan = create_plan(self.brief)
        self.assertEqual([x["format"] for x in plan["deliverables"]], ["carousel", "reel", "story"])
        self.assertIn("completion rate", plan["measurement"])
        self.assertIn("Obtain human approval before publishing.", plan["review_checklist"])

    def test_rejects_unknown_platform(self):
        with self.assertRaisesRegex(ValueError, "platform"):
            Brief("A", "B", "education", "unknown", "topic")

    def test_rejects_unknown_goal(self):
        with self.assertRaisesRegex(ValueError, "goal"):
            Brief("A", "B", "unverified", "x", "topic")

    def test_rejects_empty_fields(self):
        with self.assertRaisesRegex(ValueError, "brand"):
            Brief("  ", "B", "education", "x", "topic")

    def test_cli_success(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "brief.json"
            path.write_text(json.dumps(self.brief.__dict__), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "creative_agent", str(path)],
                capture_output=True, text=True, check=False
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["brief"]["brand"], "Example Studio")

    def test_cli_bad_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "brief.json"
            path.write_text('{"platform": "x"}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "creative_agent", str(path)],
                capture_output=True, text=True, check=False
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid brief", result.stderr)


if __name__ == "__main__":
    unittest.main()
