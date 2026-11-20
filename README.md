# Creative Agent — AI-Agent-2.0

A modular creative-strategy and production-assistant project for social media planning, design direction, video scripting, and reusable brand knowledge.

## Status

**Milestones 1–6 implemented:** deterministic planner, review-gated pipeline, optional OpenAI provider, approved-asset retrieval, supervisor, and a local browser dashboard.

The current implementation provides dependency-free, editable creative strategy, copywriting scaffolds, and video-storyboard templates. It does **not** call an AI model, research factual claims, scrape social media, or publish content. Human review decisions are recorded, but even an approved result cannot auto-publish. An optional provider adapter is available for configured live calls; no live model call is made in CI. Milestone 4 adds a local keyword retrieval prototype, a supervisor that composes specialist modules, and a read-only tool adapter interface. There is **no live MCP client or server connection**, vector embedding database, or autonomous remote tool execution; these remain potential later integrations.

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

## Milestone 4: approved assets and supervised coordination

Run the completely local demonstration (no API key or internet required):

```bash
python -m examples.supervisor_demo
```

The `KnowledgeStore.from_json(path)` API loads bounded local JSON asset records. Each record has `id`, `brand`, `title`, `text`, `source`, and **explicit boolean** `approved`. Only approved assets for the **exact matching brand** are retrievable. Retrieval uses transparent keyword overlap, with limited snippets and source IDs for tracing; this is a **lexical retrieval prototype**, not vector/semantic RAG and not fact verification.

The `coordinate(brief, store=store)` supervisor runs local planning and retrieval, records the proposed specialist workflow and required human review, and always keeps `publishable = false`. An optional `generator(brief, module, references)` callback can be injected by a developer to generate the three specialist outputs using retrieved references. That callback must enforce its own authentication, costs, networking and privacy policies. Retrieved text is **untrusted data**, not instructions, and humans must review claims and provenance before use. The existing OpenAI provider adapter is **not automatically linked** to this callback.

`ReadOnlyGateway` provides an **opt-in integration interface**, not an implementation of the Model Context Protocol. It denies calls without an explicit consent flag and only invokes explicitly registered `read_` tools. Register **trusted** read-only functions only: tool names and consent checks cannot prove that a callable has no side effects. No MCP credentials, remote servers, or publishing tools are configured.

The fictional demo assets are not real brand materials. Never commit proprietary client assets, private customer data or credentials; use secure local storage and permission checks before real deployments.

## Milestone 5: local dashboard

Run the dashboard on your own computer:

```bash
python -m creative_agent.dashboard
```

Visit **http://127.0.0.1:8765** in your browser. The app binds only to loopback and serves its own single-page HTML interface. It does not deploy to the public internet, call any AI provider, or publish to social media.

Dashboard features:
- Create creative briefs and inspect campaign strategy, draft copy, video plan and approved reference matches.
- Export campaign drafts as local JSON files. A user can record review approval in the current browser session; export to retain that review record. Approval never triggers publishing.
- Add brand-reference text to a local JSON file as **unapproved**. Explicitly approve/revoke each reference. Only approved, matching-brand records are retrieved.
- View all stored references and their review status. This single-user local prototype has no login, team collaboration, cloud sync, or audit history.
- The optional LLM adapter from Milestone 3 is **not connected to the browser dashboard**. No live generation is available in this interface yet.

The local reference store defaults to `~/.creative-agent/assets.json` and is ignored by Git. You can override its path with `CREATIVE_AGENT_ASSETS_FILE`. Treat the file as confidential and back it up yourself. The browser interface is for trusted local use only; do not expose its port through reverse proxies, containers or remote tunnels.

## Milestone 6: AI opt-in and durable draft history

The local dashboard can now record **offline draft history, human review decisions, and approved/reference workflows**, stored in `~/.creative-agent/drafts.json` by default. Saved drafts are private local JSON files with restricted file permissions, not cloud-synced. Review decisions remain non-publishing. The dashboard includes a saved-draft history panel, one-module AI generator, and explicit confirmation that the request may incur an API charge.

**Live AI is disabled by default.** To opt in, configure these environment variables on your trusted local machine (never commit API keys):
- `CREATIVE_AGENT_ENABLE_AI=1`
- `OPENAI_API_KEY` — your own provider credential
- `CREATIVE_AGENT_MODEL` — a model that supports Chat Completions JSON mode
- `CREATIVE_AGENT_INPUT_USD_PER_MILLION` and `CREATIVE_AGENT_OUTPUT_USD_PER_MILLION` — your verified current price estimates
- `CREATIVE_AGENT_REQUEST_CAP_USD` — positive estimated per-request cap

The browser **never receives the API key**. Every request requires a separate user confirmation; one click requests **one specialist module** only, not all three. The server rejects requests if AI is disabled, consent is absent, or the configured preflight **estimated** budget would be exceeded. This preflight is not a guaranteed spending cap or current pricing verification. Charges, if any, depend on your provider account and usage. Brand knowledge references are **not sent** to the provider; only the brief is sent.

The dashboard is still restricted to `127.0.0.1`. It now also validates the exact local Host header for data reads, reducing DNS-rebinding exposure. Do not place it behind a public proxy or run it on a shared multi-user host. No login system is provided. Generated claims still need human verification; review does not publish anything.

**Testing:** Unit and HTTP tests run without live API keys or charges. There is no end-to-end paid-model evaluation in CI and no guarantee of artistic quality.

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
  knowledge.py     # Approved, brand-scoped keyword retrieval
  supervisor.py    # Orchestration and human review handoff
  integrations.py  # Opt-in trusted read-only tool interface
  dashboard.py     # Loopback-only local web service
  history.py       # Local persistent drafts and review decisions
examples/
  sample_brief.json
  campaign_demo.py
  supervisor_demo.py
  knowledge_demo.json
tests/
  test_planner.py
  test_pipeline.py
  test_ai_provider.py
  test_evaluation.py
  test_milestone4.py
  test_dashboard.py
  test_history_ai_dashboard.py
evaluation/
  fixtures.json
  offline_eval.py
web/
  index.html
.github/workflows/
  quality.yml
```

## Roadmap

1. **Milestone 1:** validate briefs, suggest formats and review criteria; CLI, tests, automated quality checks.
2. **Milestone 2:** content strategy, copywriting and video-script modules with defined contracts and human approval records (**implemented as deterministic scaffolds**).
3. **Milestone 3:** optional JSON model-provider adapter, tests with fake transport, offline contract fixtures, and preflight estimated per-request cost cap (**implemented**).
4. **Milestone 4:** local approved-asset retrieval, supervised specialist coordination and trusted read-only integration contract (**implemented as offline prototypes**; live MCP, vector RAG, and autonomous agents are not implemented).
5. **Milestone 5:** responsive local browser dashboard for briefs, drafts, review and reference management (**implemented**).
6. **Milestone 6:** explicitly opt-in single-module provider calls in the local dashboard, durable draft history, human review records, and additional HTTP security checks (**implemented**, with no paid live-model integration tests).

## Design principles

Human-in-the-loop creative review; no automatic publishing; verifiable claims; explicit permission for brand assets; tests before releases; and no credentials committed to source control.

Maintainer: [JoCoded](https://github.com/JoCoded)
