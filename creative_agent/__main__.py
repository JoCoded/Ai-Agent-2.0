"""Run: python -m creative_agent examples/sample_brief.json"""

import json
import sys
from pathlib import Path

from .planner import Brief, create_plan


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage: python -m creative_agent path/to/brief.json", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("brief JSON must contain an object")
        plan = create_plan(Brief(**data))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Invalid brief: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
