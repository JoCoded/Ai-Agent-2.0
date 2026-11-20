"""Small, offline approved-asset retrieval store; no embedding service or network."""
from dataclasses import dataclass
import json
from pathlib import Path
import re

_WORDS = re.compile(r"[a-z0-9]+")
MAX_ASSETS = 1000
MAX_BODY = 4000


def _terms(text: str) -> set[str]:
    return set(_WORDS.findall(text.casefold()))


@dataclass(frozen=True)
class Asset:
    id: str
    brand: str
    title: str
    text: str
    approved: bool
    source: str

    def __post_init__(self) -> None:
        for field in ("id", "brand", "title", "text", "source"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a nonempty string")
        if type(self.approved) is not bool:
            raise ValueError("approved must be a boolean")
        if len(self.text) > MAX_BODY:
            raise ValueError("asset text too long")


class KnowledgeStore:
    """Only explicitly approved assets are searchable; brands are isolated."""

    def __init__(self, assets: list[Asset]) -> None:
        if len(assets) > MAX_ASSETS:
            raise ValueError("too many assets")
        ids = [asset.id for asset in assets]
        if len(ids) != len(set(ids)):
            raise ValueError("asset ids must be unique")
        self._assets = tuple(assets)

    @classmethod
    def from_json(cls, path: str | Path) -> "KnowledgeStore":
        path = Path(path)
        if path.stat().st_size > 2_000_000:
            raise ValueError("knowledge file too large")
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("knowledge must contain an array of assets")
        return cls([Asset(**record) for record in records])

    def retrieve(self, *, brand: str, query: str, limit: int = 3) -> list[dict]:
        if not isinstance(brand, str) or not brand.strip():
            raise ValueError("brand is required")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query is required")
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("limit must be 1-5")
        terms = _terms(query)
        ranked = []
        for asset in self._assets:
            if not asset.approved or asset.brand.casefold().strip() != brand.casefold().strip():
                continue
            overlap = len(terms & _terms(asset.title + " " + asset.text))
            if overlap:
                ranked.append((overlap, asset))
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        return [
            {"id": asset.id, "title": asset.title, "excerpt": asset.text[:1200],
             "source": asset.source, "score": score, "approved": True}
            for score, asset in ranked[:limit]
        ]
