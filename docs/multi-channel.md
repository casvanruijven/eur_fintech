# Multi-channel delivery

## NFC is one channel, not the product

The product is the **structured receipt object** and the infrastructure around it. NFC is simply one
way to put the receipt's `delivery_url` in front of the customer. The same object can be delivered
through any channel — the data model never changes.

## Channels in the MVP

| Channel | Flow | How the customer gets it |
|---|---|---|
| **NFC** | `/merchant` | Tap a tile at the till → the tile carries `/receipt/{id}` (simulated by "Simulate customer tap"). |
| **Online link** | `/online-checkout` | After paying in a webshop, a "View your ZZPay receipt" link opens `/receipt/{id}`. |

Both flows call the **same** `POST /api/checkout` and produce the **same** `Receipt`; only the
`channel` field (`NFC` vs `ONLINE_LINK`) differs. The public receipt page is identical for both.

```
                       POST /api/checkout
   NFC tile  ┐                                   ┌  Receipt object  ─►  /receipt/{id}
   Online    ┤ ──►  Receipt Service (einvoice) ──┤  (channel field only differs)
   (QR/email/POS API — future)                   └
```

## Future channels (same object underneath)

- **QR code** on a paper slip or screen → opens the same URL.
- **Email** the link directly to the buyer at checkout.
- **App notification** for users who do install something later.
- **POS API** — the till pushes the basket straight to `POST /api/checkout`.

Because every channel resolves to one structured object, adding a channel is an integration detail,
not a re-architecture.

## Network effects

Each side reinforces the other on shared infrastructure:

- **More merchants** generating receipts → more ZZP'ers encounter ZZPay receipts in the wild, with no
  app to install → more accounts that configure an accountant.
- **More ZZP'ers** expecting ZZPay receipts → more reason for merchants to enable the (low-effort)
  tile/link.
- **Accountants** receiving clean EN 16931 UBL from many of their clients → they start *recommending*
  ZZPay, pulling in both merchants and ZZP'ers.

The single structured object is the asset that compounds across all three sides.
