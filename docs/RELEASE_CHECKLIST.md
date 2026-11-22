# Local release readiness checklist

This checklist is for the **single-user loopback dashboard**, not public production deployment.

## Automated (required)

- [ ] Python 3.11, 3.12 and 3.13 test matrix passes on the PR and on `main`.
- [ ] Offline creative evaluation passes with no network requests or API credentials.
- [ ] Concurrent draft and asset writes retain all records; only one reviewer decision can win.
- [ ] Full HTTP workflow passes: create unapproved reference, approve, retrieve, plan, review, reload.
- [ ] Host-header and cross-origin restrictions reject unauthorized requests.
- [ ] AI-off setting rejects generation and creates no draft.

## Manual browser and accessibility review (not established by CI)

- [ ] Launch `python -m creative_agent.dashboard` and open `http://127.0.0.1:8765`.
- [ ] Test 375px mobile width, tablet and desktop; inspect scrolling, spacing and button focus.
- [ ] Navigate with keyboard only; confirm forms, focus order and confirmation dialogues are usable.
- [ ] Create a realistic *fictional* brand brief, then review strategy, copy and video tabs.
- [ ] Add an unapproved fictional reference, verify it is not retrieved; approve it and regenerate.
- [ ] Save and reopen a draft, record reviewer decision, restart the server, verify persistence.
- [ ] Export JSON and confirm the exported contents match the visible draft.
- [ ] Verify nothing is published; no remote server or external scripts are loaded.
- [ ] Confirm backup and restore of local `assets.json` and `drafts.json`.

## Controlled live-provider evaluation (requires user's separate opt-in)

- [ ] Choose a compatible, supported model and verify up-to-date provider pricing.
- [ ] Set a low personal spend limit at the provider account level; test key in a secure local environment only.
- [ ] Configure the dashboard's AI environment variables and a conservative **estimated** request cap.
- [ ] Use a fictional, non-sensitive brief and explicitly confirm one paid request.
- [ ] Check schema validity, usefulness, placeholders, recorded token usage, and estimated cost.
- [ ] Verify that approving output never triggers publication and that no private references are sent.
- [ ] Rotate/revoke test credentials if leaked; turn `CREATIVE_AGENT_ENABLE_AI` off after testing.

## Known limitations and release decision

- Server-side locks protect concurrent requests handled by the **same running process**, not concurrent writes by multiple dashboard instances or external editors. Run only one local server instance against the data files.
- Local JSON is **not encrypted**, and the dashboard has no user authentication. It must not be publicly hosted or used on an untrusted/shared machine.
- JSON file writes are atomic, but backup/restore is the user's responsibility.
- No browser automation, accessibility audit, penetration test, real-provider execution, or production hosting test has been completed by GitHub Actions.
- A successful CI run therefore means **local prototype regression readiness**, not certification for public production deployment.

**Release gate:** no public launch until manual browser review, security assessment, and deployment-specific authentication and data-protection work are complete.
