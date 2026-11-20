"""Fully offline, read-only supervised campaign example."""
import json
from pathlib import Path

from creative_agent.knowledge import KnowledgeStore
from creative_agent.planner import Brief
from creative_agent.supervisor import coordinate

brief = Brief("Example Studio", "early-career designers", "education",
              "instagram", "portfolio development")
store = KnowledgeStore.from_json(Path(__file__).with_name("knowledge_demo.json"))
print(json.dumps(coordinate(brief, store=store), indent=2))
