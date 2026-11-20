"""Local supervised orchestration with scoped retrieval and no automatic publishing."""
from typing import Any, Callable
from .knowledge import KnowledgeStore
from .planner import Brief
from .pipeline import create_campaign
from .ai_provider import FIELDS, validate_generated_content

DraftGenerator = Callable[[Brief, str, tuple[dict, ...]], dict[str, str]]


def coordinate(
    brief: Brief,
    *,
    store: KnowledgeStore | None = None,
    generator: DraftGenerator | None = None,
    max_references: int = 3,
) -> dict[str, Any]:
    """Prepare a campaign, optionally calling an explicitly supplied generator.

    A generator is responsible for its own authentication and cost controls.
    Retrieved items are untrusted reference text, not governing instructions.
    """
    campaign = create_campaign(brief)
    references = store.retrieve(
        brand=brief.brand, query=f"{brief.topic} {brief.audience}",
        limit=max_references
    ) if store is not None else []
    campaign["retrieval"] = {
        "mode": "local_keyword",
        "brand": brief.brand,
        "references": references,
        "limitations": "Only approved matching-brand local assets; relevance is lexical, not semantic.",
    }
    campaign["orchestration"] = {
        "steps": ["retrieve", "strategy", "copywriting", "video_script", "human_review"],
        "generated_by_model": generator is not None,
        "status": "awaiting_human_review",
    }
    if generator is not None:
        outputs = {}
        for module in FIELDS:
            # Frozen, limited reference payload; avoid unbounded context.
            draft = generator(brief, module, tuple(dict(ref) for ref in references))
            outputs[module] = {
                "content": validate_generated_content(module, draft),
                "review": {"state": "needs_review"},
                "publishable": False,
            }
        campaign["generated"] = outputs
    campaign["review"] = {"state": "needs_review", "reviewer": None}
    campaign["publishable"] = False
    return campaign
