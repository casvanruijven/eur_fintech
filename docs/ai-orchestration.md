# AI agents & orchestration

## Which agents, and why

| Agent | Role | Why it was useful |
|---|---|---|
| **Claude Code** | Main coding agent | Operates on the **whole repository** with real tools — it reads existing files, edits across the FastAPI backend and React frontend in one coherent pass, runs the test suite and the production build, and fixes what it finds. Plan-mode first, so the architecture was agreed before code was written. |
| **ChatGPT** | Scoping & prompt design | Used to interpret the assignment brief, turn the Assignment 1 business model + lecturer feedback into a concrete MVP scope, and draft the prompts/plan that Claude Code then executed. |
| **Humans (the team)** | Product decisions | Every consequential choice — pivot to no-login receipts, keep the optional account for accountant forwarding, EN 16931 *core* over a token XML, refund-as-credit-note — was a human decision; the agents proposed, the team decided. |

## How it was orchestrated

1. **Interpret → scope (ChatGPT + team).** The brief, the Assignment 1 model, and the lecturer
   feedback were distilled into a narrow, demo-ready scope: merchant source → multi-channel delivery →
   public receipt → export/email/refund, with EN 16931 export and credit-note refunds.
2. **Plan (Claude Code, plan mode).** Claude Code explored the existing login-based receipt app,
   then designed the pivot as a written plan (data model, endpoints, routes, docs) reviewed and
   adjusted with the team **before** any code changed.
3. **Implement in reviewable chunks.** Backend first (models → optional auth → eInvoice mapper →
   EN 16931 UBL → routers → email/seed), then the frontend (api client → components → pages), then
   documentation. Each chunk was verified before moving on.
4. **Self-verification.** The agent ran `pytest` (14 tests, in-memory SQLite) and a production
   `npm run build` as it went, caught real issues (e.g. a Postgres foreign-key insert-ordering bug in
   the seed that SQLite had masked), and fixed them immediately.

## Why agentic coding fit this project

- **Full-repo context.** The task was a *pivot* of an existing codebase, not a greenfield build.
  An agent that reads and edits across the whole repo keeps the backend, frontend, tests, and docs
  consistent — the data model, the API client, and the documentation all moved together.
- **Tight verify loop.** Running tests and builds inside the loop turns "looks right" into "is
  green", which matters for a graded, must-run-first-time MVP.
- **Constrained by the assignment.** The agent instruction files (`CLAUDE.md`, `AGENTS.md`,
  `.agents/zzpay-mvp-agent.md`) encode the invariants — narrow scope, no-login receipts, EN 16931
  model, refund-as-credit-note — so AI suggestions were held to the assignment rather than expanding
  it.

## How agent instructions guide future changes

The instruction files tell any future coding agent to keep the MVP narrow, preserve public no-login
receipt access, preserve the EN 16931 data model and the refund-as-credit-note rule, update the docs
when features change, and avoid adding real external integrations unless explicitly asked. This keeps
the project coherent across sessions and contributors.
