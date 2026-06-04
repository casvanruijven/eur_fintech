# .claude/instructions.md

Entry point for coding agents in this repo. The authoritative guidance lives in:

- [`../CLAUDE.md`](../CLAUDE.md) — full conventions + invariants.
- [`../AGENTS.md`](../AGENTS.md) — agent-agnostic summary.
- [`../.agents/zzpay-mvp-agent.md`](../.agents/zzpay-mvp-agent.md) — task-level brief.
- [`rules/conventions.md`](rules/conventions.md) — backend/frontend conventions.

## TL;DR

ZZPay is a **narrow, demo-ready** receipt-infrastructure MVP (FinTech Assignment 2). Before changing
anything, internalise the five invariants:

1. Receipts are **public** (view + PDF/PNG, no login).
2. **JSON/UBL export + email** are **account-gated** (`CurrentUser`).
3. UBL is **EN 16931 core**; missing seller VAT → **HTTP 422**, never an invalid document.
4. **Refund = linked credit note**; never mutate the original receipt.
5. `user_id` is **nullable** and links on the first authenticated action.

Keep the scope narrow, simulate (don't build) real external integrations, and **update `README.md` +
the relevant `docs/*.md` in the same change**. Verify with `cd server && pytest` and
`cd client && npm run build` before finishing.
