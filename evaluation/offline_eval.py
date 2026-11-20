"""Offline, reproducible contract evaluation: no credentials and no network."""
import json
from pathlib import Path

from creative_agent.ai_provider import FIELDS, validate_generated_content
from creative_agent.planner import Brief
from creative_agent.pipeline import create_campaign


def evaluate(fixtures_path: Path | None = None) -> dict:
    path = fixtures_path or Path(__file__).with_name("fixtures.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("evaluation dataset is empty")
    passing = 0
    details = []
    for case in cases:
        brief = Brief(**case["brief"])
        campaign = create_campaign(brief)
        checked = (
            campaign["review"]["state"] == "needs_review"
            and campaign["publishable"] is False
            and set(case["modules"]) == set(FIELDS)
        )
        for module in case["modules"]:
            sample = {name: f"Example {name} [VERIFY]" for name in FIELDS[module]}
            checked = checked and validate_generated_content(module, sample) == sample
        details.append({"name": case["name"], "passed": checked})
        passing += int(checked)
    return {"total": len(cases), "passed": passing, "details": details}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["total"] == result["passed"] else 1)
