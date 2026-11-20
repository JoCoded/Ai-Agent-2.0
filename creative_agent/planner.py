"""Deterministic creative-planning baseline; no external API or network access."""

from dataclasses import asdict, dataclass
from typing import Any

SUPPORTED_PLATFORMS = ("instagram", "linkedin", "tiktok", "x", "youtube")
SUPPORTED_OBJECTIVES = ("awareness", "engagement", "conversion", "education")

_FORMATS = {
    "instagram": ("carousel", "reel", "story"),
    "linkedin": ("thought-leadership post", "document carousel"),
    "tiktok": ("short-form video",),
    "x": ("thread", "short post"),
    "youtube": ("short", "explainer video"),
}
_METRICS = {
    "awareness": ("reach", "impressions"),
    "engagement": ("comments", "shares", "saves"),
    "conversion": ("qualified clicks", "conversion rate"),
    "education": ("completion rate", "saves"),
}


@dataclass(frozen=True)
class Brief:
    brand: str
    audience: str
    goal: str
    platform: str
    topic: str
    tone: str = "clear and human"

    def __post_init__(self) -> None:
        for field in ("brand", "audience", "goal", "platform", "topic", "tone"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if self.platform.strip().lower() not in SUPPORTED_PLATFORMS:
            raise ValueError(f"platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
        if self.goal.strip().lower() not in SUPPORTED_OBJECTIVES:
            raise ValueError(f"goal must be one of: {', '.join(SUPPORTED_OBJECTIVES)}")


def create_plan(brief: Brief) -> dict[str, Any]:
    """Return a structured production brief for human review, not AI-generated copy."""
    platform = brief.platform.strip().lower()
    goal = brief.goal.strip().lower()
    topic = brief.topic.strip()
    audience = brief.audience.strip()
    return {
        "brief": asdict(brief),
        "positioning": f"Help {audience} understand {topic} through {brief.brand.strip()}.",
        "creative_direction": {
            "tone": brief.tone.strip(),
            "opening_hook": f"What should {audience} know about {topic}?",
            "core_message": f"Explain {topic} with one specific, verifiable takeaway.",
            "cta": "Invite the audience to ask a relevant question.",
        },
        "deliverables": [
            {"format": name, "status": "proposed"}
            for name in _FORMATS[platform]
        ],
        "measurement": list(_METRICS[goal]),
        "review_checklist": [
            "Check every factual claim against a reliable source.",
            "Confirm brand voice, audience relevance, and platform fit.",
            "Verify consent and usage rights for creative assets.",
            "Review accessibility, captions, and legibility.",
            "Obtain human approval before publishing.",
        ],
    }
