# Merchant adoption, costs & support

This document answers the lecturer feedback head-on: merchants must support ZZPay, the adoption
hurdle must be low, and **costs — especially support — were underestimated**.

## Low adoption hurdle by design

- **ZZPay does not replace the POS.** In the MVP the merchant side is a lightweight portal that turns
  a basket into a receipt; in production it is a thin integration (a tile, a link, or a single
  webhook), not a new checkout system. The merchant keeps their existing till.
- **No customer app.** Because the buyer just opens a URL in their browser, the merchant doesn't have
  to convince customers to install anything — the single biggest adoption killer for receipt apps.
- **Pilot-ready, not platform-ready.** The MVP intentionally ships the *narrow* pilot path (one tile
  / one link), so a pilot merchant can be live in minutes. The expensive, deep POS integrations come
  later and only for merchants that convert.

## Where the real costs are

| Cost area | MVP stance | Production reality |
|---|---|---|
| **POS integration** | Simulated (`MERCHANTS` registry) | The dominant cost: every POS vendor (and version) is a separate integration + certification + maintenance. |
| **Merchant support** | None needed (it's a demo) | **The most underestimated cost.** Tiles fail, receipts "don't appear", staff need training, refunds confuse cashiers. Support scales with merchant count, not revenue. |
| **Customer support** | None | "Where's my receipt?", "wrong email", refund questions — high volume, low value each. |
| **Email deliverability** | Mocked | SPF/DKIM/DMARC, bounce handling, and a paid provider at volume. |
| **Compliance** | EN 16931 core, not certified | A certified Peppol Access Point + ongoing standard updates is a recurring cost. |

## How the MVP keeps support manageable

- **Status on every receipt** (`GENERATED → VIEWED → SENT → REFUNDED`) and a **merchant receipts
  dashboard** (`/merchant/receipts`) give first-line support an instant answer to "what happened to
  this receipt?" without a database query. This is the seed of a per-receipt support log.
- **Auditable refunds** (linked credit notes) mean a refund question has a single, correct answer
  instead of a "did someone edit it?" investigation.
- **Self-service export** (PDF/PNG public; UBL/email self-serve once logged in) deflects the most
  common tickets ("can you resend it?").

## Honest risk statement

Support and POS-integration cost — not technology — is the main risk to ZZPay's unit economics.
The MVP is scoped to validate demand and the core flow **before** committing to those costs: prove
that merchants will enable a tile and that ZP'ers value the structured receipt, then invest in deep
integrations only where the pilots convert.
