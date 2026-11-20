from __future__ import annotations
"""Local draft archive, atomic writes and explicit human review."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4


class HistoryStore:
    MAX_ENTRIES = 200
    MAX_FILE_BYTES = 2_000_000

    def __init__(self, path: Path):
        self.path = Path(path)

    def list(self) -> list[dict]:
        if not self.path.exists():
            return []
        if self.path.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError("draft archive exceeds size limit")
        records = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("invalid draft archive")
        return records

    def _save(self, records: list[dict]) -> None:
        if len(records) > self.MAX_ENTRIES:
            raise ValueError("draft history limit reached")
        data = json.dumps(records, ensure_ascii=False, indent=2)
        if len(data.encode("utf-8")) > self.MAX_FILE_BYTES:
            raise ValueError("draft archive exceeds size limit")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, tmp = tempfile.mkstemp(prefix=".draft-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def add(self, campaign: dict, *, kind: str) -> dict:
        if kind not in ("offline", "ai"):
            raise ValueError("invalid draft type")
        if not isinstance(campaign, dict) or campaign.get("publishable") is not False:
            raise ValueError("only unpublishable drafts can be archived")
        if not isinstance(campaign.get("brief"), dict):
            raise ValueError("draft brief is missing")
        row = {
            "id": str(uuid4()),
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "brief": campaign["brief"],
            "campaign": campaign,
            "review": {"state": "needs_review", "reviewer": None, "notes": "", "reviewed_at": None},
        }
        records = self.list()
        records.insert(0, row)
        self._save(records)
        return row

    def decide(self, identifier: str, *, reviewer: str, approve: bool, notes: str = "") -> dict:
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("missing draft id")
        if type(approve) is not bool:
            raise ValueError("approve must be boolean")
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 100:
            raise ValueError("human reviewer name required")
        if not isinstance(notes, str) or len(notes) > 1000:
            raise ValueError("notes too long")
        records = self.list()
        for row in records:
            if row["id"] == identifier:
                if row["review"]["state"] != "needs_review":
                    raise ValueError("draft has already been reviewed")
                row["review"] = {
                    "state": "approved" if approve else "changes_requested",
                    "reviewer": reviewer.strip(),
                    "notes": notes,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                }
                # Never authorize publishing, regardless of review outcome.
                row["campaign"]["publishable"] = False
                self._save(records)
                return row
        raise ValueError("draft not found")
