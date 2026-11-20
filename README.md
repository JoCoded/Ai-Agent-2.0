# Creative Agent — AI-Agent-2.0

A modular creative-strategy and production-assistant project for social media planning, design direction, video scripting, and reusable brand knowledge.

## Status

**Milestones 1–3 implemented:** deterministic planner, review-gated creative pipeline, and an opt-in OpenAI Chat Completions JSON-generation adapter with offline contract evaluation.

The current implementation provides dependency-free, editable creative strategy, copywriting scaffolds, and video-storyboard templates. It does **not** call an AI model, research factual claims, scrape social media, or publish content. Human review decisions are recorded, but even an approved result cannot auto-publish. An optional provider adapter is available for configured live calls; no live model call is made in CI. MCP tools, RAG and autonomous supervision remain planned.

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

## Milestone 2: specialist production modules

Run the full strategy + copy + video proposal:

```bash
python examples/campaign_demo.py
```

The `creative_agent.pipeline` module provides `strategy(brief)`, `copywriting(brief)`, `video_script(brief)`, and `create_campaign(brief)`. Every campaign starts with `review.state = needs_review` and `publishable = false`. A human can record `request_review_decision(campaign, reviewer=..., approve=..., notes=...)`; this records a review outcome **without publishing** or enabling automatic publication. Output contains explicitly marked placeholders for claims that require sourcing and review. These are transparent deterministic templates, **not** model-generated copy.

## Milestone 3: optional live language model

This adapter uses the OpenAI Chat Completions JSON-object interface over HTTPS with Python standard-library networking. The adapter is **not** activated automatically, and no key is shipped in this repository. Choose a model that supports JSON-object response formatting.

Set `OPENAI_API_KEY` in your **local environment** (or use a secret manager, never commit it). Import `Brief` from `creative_agent`, then call `generate` from `creative_agent.ai_provider` with a `GenerationSettings(model="YOUR_SUPPORTED_MODEL")` and `module="strategy"`, `"copywriting"`, or `"video_script"`. The optional `generate_campaign` function invokes all three modules; this can result in **three billable API calls**. There is no live-key command, no automatic CI live call, and no auto-publication.

Security and reliability measures:
- API calls require explicit invocation and a key; keys are never printed or persisted by the adapter.
- Fixed HTTPS endpoint; network requests have timeouts and limited response size.
- Strict JSON output validation: exact expected keys, nonempty strings, and bounded field lengths. Fail closed on invalid provider output.
- Hard `max_completion_tokens` per request, input byte limits, and configurable timeout. These cap request sizes, **not total account spending**.
- Optional preflight **estimated** USD request cap, requiring caller-supplied input and output prices per million tokens. The calculation conservatively uses input UTF-8 bytes as a token-count proxy; this is **not a guaranteed billing or account spending limit**. Verify the model's current prices yourself.
- Provider errors expose sanitized messages rather than raw HTTP bodies or credentials.
- Generated drafts retain `review.state = needs_review` and `publishable = false`. Model output is unverified until a human checks it.

The evaluation fixtures check structural contracts and review-state invariants offline, **not factual accuracy or model creative quality**. Live-model evaluations should be introduced later with opt-in keys, budgets, and human review.

## Quality checks

```bash
python -m compileall -q creative_agent tests evaluation
python -m unittest discover -s tests -v
python -m evaluation.offline_eval
```

GitHub Actions runs these checks on pushes, pull requests, once daily (06:17 UTC, best effort), and manually. The workflow also runs the sample CLI on Python 3.11, 3.12, and 3.13. Scheduled workflow runs only execute from GitHub's default branch after merge.

## Project structure

```text
creative_agent/
  __init__.py      # Public API
  planner.py       # Brief validation and deterministic planning
  __main__.py      # JSON-to-JSON command-line interface
  pipeline.py      # Strategy, copy, video and review gates
  ai_provider.py   # Opt-in JSON LLM adapter, usage and cost estimates
examples/
  sample_brief.json
  campaign_demo.py
tests/
  test_planner.py
  test_pipeline.py
  test_ai_provider.py
  test_evaluation.py
evaluation/
  fixtures.json
  offline_eval.py
.github/workflows/
  quality.yml
```

## Roadmap

1. **Milestone 1:** validate briefs, suggest formats and review criteria; CLI, tests, automated quality checks.
2. **Milestone 2:** content strategy, copywriting and video-script modules with defined contracts and human approval records (**implemented as deterministic scaffolds**).
3. **Milestone 3:** optional JSON model-provider adapter, tests with fake transport, offline contract fixtures, and preflight estimated per-request cost cap (**implemented**).
4. **Milestone 4:** opt-in MCP integrations, RAG asset library, and supervised multi-agent execution.

## Design principles

Human-in-the-loop creative review; no automatic publishing; verifiable claims; explicit permission for brand assets; tests before releases; and no credentials committed to source control.

Maintainer: [JoCoded](https://github.com/JoCoded)
