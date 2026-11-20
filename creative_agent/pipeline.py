"""Composable, provider-free creative production modules and approval gates.

These modules propose structured drafts; they do not call an LLM or publish.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .planner import Brief, create_plan

VALID_STATES = ("needs_review", "approved", "changes_requested")
SUPPORTED_ASSET_TYPES = ("post", "video")


@dataclass(frozen=True)
class Review:
    """Human review decision; no publishing is performed by this module."""
    state: str = "needs_review"
    reviewer: str | None = None
    notes: str = ""
    reviewed_at: str | None = None

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError("unknown review state")
        if self.state != "needs_review" and (
            not self.reviewer or not self.reviewer.strip() or not self.reviewed_at
        ):
            raise ValueError("a human reviewer and review timestamp are required for a decision")
        if self.state == "needs_review" and (self.reviewer or self.reviewed_at):
            raise ValueError("pending work cannot claim a completed review")


def strategy(brief: Brief) -> dict[str, Any]:
    """Provide an objective, audience, content pillars, and evaluation criteria."""
    base = create_plan(brief)
    topic = brief.topic.strip()
    return {
        "module": "content_strategist",
        "audience": brief.audience.strip(),
        "objective": brief.goal.strip().lower(),
        "key_message": base["creative_direction"]["core_message"],
        "content_pillars": [
            {"name": "Explain", "angle": f"Introduce {topic} in plain language."},
            {"name": "Demonstrate", "angle": f"Show a specific example of {topic}."},
            {"name": "Engage", "angle": f"Ask the audience what they want to learn about {topic}."},
        ],
        "success_metrics": base["measurement"],
        "assumptions_to_verify": ["Audience needs and factual claims are unverified."],
    }


def copywriting(brief: Brief) -> dict[str, Any]:
    """Generate editable copy scaffolding, not invented facts."""
    topic = brief.topic.strip()
    audience = brief.audience.strip()
    return {
        "module": "copywriting",
        "platform": brief.platform.strip().lower(),
        "tone": brief.tone.strip(),
        "headline": f"{topic}: what {audience} should know",
        "caption": (
            f"Let's talk about {topic}. Here's one useful idea to explore: "
            f"[add a sourced insight relevant to {audience}]. "
            "What would you like us to cover next?"
        ),
        "cta": "Ask a specific question in the comments.",
        "required_edits": [
            "Replace the bracketed placeholder with a verified, relevant insight.",
            "Check brand voice and platform length before approving.",
        ],
        "status": "draft",
    }


def video_script(brief: Brief) -> dict[str, Any]:
    """Create a concise scene-by-scene storyboard for an editor to refine."""
    topic = brief.topic.strip()
    return {
        "module": "video_script",
        "target_duration_seconds": 30,
        "scenes": [
            {"start": 0, "end": 5, "purpose": "hook", "voiceover": f"Here's a question about {topic}.", "visual": "Relevant licensed opening footage"},
            {"start": 5, "end": 20, "purpose": "explain", "voiceover": "[insert verified explanation and example]", "visual": "Supporting demonstration or graphics"},
            {"start": 20, "end": 27, "purpose": "takeaway", "voiceover": "[insert one verified actionable takeaway]", "visual": "One key statement with accessible captions"},
            {"start": 27, "end": 30, "purpose": "cta", "voiceover": "What would you like to learn next?", "visual": "Brand end card"},
        ],
        "production_checks": [
            "Validate every claim and on-screen statistic.",
            "Clear music and footage rights.",
            "Add captions and verify readable contrast.",
        ],
        "status": "draft",
    }


def create_campaign(brief: Brief) -> dict[str, Any]:
    """Compose the specialist modules into a review-required campaign proposal."""
    return {
        "schema_version": "2.0",
        "brief": asdict(brief),
        "strategy": strategy(brief),
        "copywriting": copywriting(brief),
        "video_script": video_script(brief),
        "review": asdict(Review()),
        "publishable": False,
        "limitations": [
            "Templates only; no live research, generative model, or source verification.",
            "Human approval is mandatory before any external publishing.",
        ],
    }


def request_review_decision(
    campaign: dict[str, Any], *, reviewer: str, approve: bool, notes: str = ""
) -> dict[str, Any]:
    """Record an explicit reviewer decision; still never auto-publish."""
    if not isinstance(campaign, dict) or campaign.get("schema_version") != "2.0":
        raise ValueError("expected a milestone-2 campaign")
    if campaign.get("review", {}).get("state") != "needs_review":
        raise ValueError("campaign already reviewed")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("reviewer must be a non-empty string")
    if not isinstance(notes, str):
        raise ValueError("notes must be a string")
    decision = Review(
        state="approved" if approve else "changes_requested",
        reviewer=reviewer.strip(),
        notes=notes,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    updated = dict(campaign)
    updated["review"] = asdict(decision)
    # Approval is a documentation decision, NOT authorization to auto-publish.
    updated["publishable"] = False
    return updated
