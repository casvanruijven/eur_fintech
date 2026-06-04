# Assignment mapping

How each Assignment 2 requirement is satisfied, and where to find it.

| Assignment requirement | Where implemented | Explanation |
|---|---|---|
| **Working MVP of the Assignment 1 model** | whole repo | A merchant creates a structured receipt; it is delivered via NFC/online; the customer views/exports/emails/refunds it in a browser. |
| **Main feature: capture data at the source** | `routers/checkout.py`, `einvoice.py` | A basket is mapped into a typed `Receipt` at checkout — no scanning/OCR. |
| **Main feature: NFC delivery** | `pages/MerchantCheckout.tsx` | "Generate ZZPay Receipt" → "Simulate customer tap" opens `/receipt/:id`. NFC tap is simulated (documented). |
| **Main feature: multi-channel** | `pages/OnlineCheckout.tsx`, `docs/multi-channel.md` | The online checkout delivers the *same* receipt object through a link instead of a tile. |
| **Main feature: no-login receipt access** | `pages/ReceiptView.tsx`, `routers/receipts.py` (public GET) | The public page renders without auth; PDF/PNG download is public. |
| **Main feature: export PDF/PNG** | `pdf.py`, `ExportButtons.tsx` | Pure-Python rendering (xhtml2pdf + pypdfium2). |
| **Main feature: export JSON + UBL** | `einvoice.py`, `ubl.py` | Structured JSON twin + EN 16931 core UBL 2.1 (account-gated). |
| **Main feature: email to self / accountant** | `email.py`, `routers/receipts.py` | Mock email (PDF + UBL); status recorded on the receipt. |
| **Main feature: returning-user preferences** | `lib/storage-service.ts`, `PreferencesForm.tsx` | `localStorage` remembers details on the device; optional account remembers the accountant + JWT. |
| **Refunds / returns** | `routers/refunds.py`, `RefundPanel.tsx`, `docs/refund-flow.md` | Linked credit note; original preserved; SENT-warning. |
| **eInvoice standard (EN 16931)** | `ubl.py`, `docs/einvoice-standard.md` | EN 16931 core UBL with the mandatory business terms; 422 if seller VAT missing. |
| **Architecture explanation** | `docs/architecture.md`, `README.md §6` | Text diagram + component walkthrough. |
| **Deployment explanation** | `README.md §4–5` | Local run + deployment notes (env-driven config, health check). |
| **Investor orientation** | `pages/Landing.tsx`, `README.md` | The landing page and README carry the investor narrative. |
| **AI coding agents used** | `docs/ai-orchestration.md` | Claude Code (main) + ChatGPT (scoping); human decisions. |
| **Clean public repo + README** | `README.md`, `docs/` | Concise but complete documentation in the root + `docs/`. |
| **Agent instruction files** | `CLAUDE.md`, `AGENTS.md`, `.agents/zzpay-mvp-agent.md`, `.claude/` | Guide future agents to keep the scope and invariants. |
| **Repo description & topic tags** | `README.md` (Suggested GitHub metadata) | Description + topic tags to set on GitHub. |

## Service-file name mapping (assignment §8 → real files)

The assignment lists frontend-style service names; in this FastAPI + React MVP the logic splits
across backend Python modules and frontend libs. The mapping:

| Assignment name | Real file(s) | Role |
|---|---|---|
| `receipt-service` | `server/app/einvoice.py` + `client/src/api.ts` | create/retrieve receipts |
| `einvoice-mapper` | `server/app/einvoice.py` | basket/POS → eInvoice receipt object |
| `export-service` | `server/app/einvoice.py` (JSON) + `server/app/ubl.py` (UBL) + `server/app/pdf.py` (PDF/PNG) + `client/src/lib/download.ts` | export to JSON/UBL/PDF/PNG |
| `refund-service` | `server/app/routers/refunds.py` + `server/app/einvoice.py` (`credit_from_receipt`) | linked credit notes |
| `email-service` | `server/app/email.py` | mock/SMTP send with PDF + UBL |
| `storage-service` | `client/src/lib/storage-service.ts` | browser localStorage preferences |
