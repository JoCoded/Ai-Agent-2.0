# Creative Agent — AI-Agent-2.0

A modular creative-strategy and production-assistant project for social media planning, design direction, video scripting, and reusable brand knowledge.

## Status

**Milestone 1: deterministic Python creative-brief planner (implemented).**

This milestone provides a working, dependency-free baseline for turning a structured brief into a proposed creative plan. It does **not** call an AI model, scrape social media, publish content, or claim to provide live trend analysis. The multi-agent supervisor, MCP tools, retrieval-augmented memory, and design/video integrations below remain **planned**.

## Quick start

Requires Python 3.11 or newer. No third-party packages are needed.

```bash
python -m creative_agent examples/sample_brief.json
```

It prints JSON containing:
- The supplied brief and positioning statement
- A draft creative direction and opening-hook prompt
- Platform-specific suggested deliverable formats
- Goal-specific measurement metrics
- A human review checklist for factual accuracy, rights, accessibility, and approvals

Edit the example JSON to provide your own brand, audience, goal, platform, topic, and optional tone. Supported platforms: `instagram`, `linkedin`, `tiktok`, `x`, and `youtube`. Goals: `awareness`, `engagement`, `conversion`, and `education`.

## Quality checks

```bash
python -m compileall -q creative_agent tests
python -m unittest discover -s tests -v
```

GitHub Actions runs these checks on pushes, pull requests, once daily (06:17 UTC, best effort), and manually. The workflow also runs the sample CLI on Python 3.11, 3.12, and 3.13. Scheduled workflow runs only execute from GitHub's default branch after merge.

## Project structure

```text
creative_agent/
  __init__.py      # Public API
  planner.py       # Brief validation and deterministic planning
  __main__.py      # JSON-to-JSON command-line interface
examples/
  sample_brief.json
tests/
  test_planner.py
.github/workflows/
  quality.yml
```

## Roadmap

1. **Milestone 1:** validate briefs, suggest formats and review criteria; CLI, tests, automated quality checks.
2. **Milestone 2:** dedicated copy, design, and video-script modules with defined contracts and human approval steps.
3. **Milestone 3:** optional model-provider adapters with safe secret handling, evaluation datasets, and cost limits.
4. **Milestone 4:** opt-in MCP integrations, RAG asset library, and supervised multi-agent execution.

## Design principles

Human-in-the-loop creative review; no automatic publishing; verifiable claims; explicit permission for brand assets; tests before releases; and no credentials committed to source control.

Maintainer: [JoCoded](https://github.com/JoCoded)
