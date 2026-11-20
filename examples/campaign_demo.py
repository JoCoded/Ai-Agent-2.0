"""Demonstrate the complete campaign pipeline without network access."""
import json

from creative_agent import Brief
from creative_agent.pipeline import create_campaign

brief = Brief(
    brand="Example Studio",
    audience="early-career designers",
    goal="education",
    platform="instagram",
    topic="building a practical portfolio",
    tone="warm, direct, and useful",
)
print(json.dumps(create_campaign(brief), indent=2))
