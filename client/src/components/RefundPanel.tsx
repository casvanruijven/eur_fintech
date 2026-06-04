// Request a refund / return. Refunds are modeled as linked credit notes — the
// original receipt is never deleted or edited. Supports item-level refunds (pick
// the returned line, e.g. "Kit") or a full refund.
import { useState } from "react";
import { PiArrowUDownLeft } from "react-icons/pi";
import type { Receipt } from "../api";
import * as api from "../api";
import { Button } from "./Button";
import { Card } from "./Card";
import { euro, lineGross } from "../lib/format";

export function RefundPanel({
  receipt,
  onRefunded,
}: {
  receipt: Receipt;
  onRefunded: () => void;
}) {
  const [selected, setSelected] = useState<number[]>([]);
  const [full, setFull] = useState(false);
  const [reason, setReason] = useState("Customer returned unused item");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const alreadySent = receipt.status === "SENT";

  function toggle(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function submit() {
    setError(null);
    setWarning(null);
    if (!full && selected.length === 0) {
      setError("Select at least one item to refund, or choose a full refund.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.refundReceipt(receipt.invoice_id, {
        full,
        line_ids: full ? [] : selected,
        reason,
      });
      setWarning(res.warning);
      onRefunded();
    } catch (e) {
      setError(api.apiError(e, "Could not create the credit note"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-5">
      <h3 className="text-base font-semibold text-gray-900">Request a refund / return</h3>
      <p className="mt-1 text-sm text-gray-500">
        ZZPay creates a <strong>linked credit note</strong> — the original receipt stays
        valid and auditable.
      </p>

      {alreadySent && (
        <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          This receipt was already sent to your accountant. ZZPay will create a linked
          credit note so the correction remains auditable.
        </div>
      )}

      <div className="mt-4 space-y-2">
        {receipt.invoice_lines.map((line) => (
          <label
            key={line.id}
            className={`flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm ${
              full ? "opacity-40" : "hover:border-brand/40"
            } ${selected.includes(line.id) ? "border-brand bg-brand/5" : "border-gray-200"}`}
          >
            <span className="flex items-center gap-2">
              <input
                type="checkbox"
                disabled={full}
                checked={selected.includes(line.id)}
                onChange={() => toggle(line.id)}
              />
              {line.quantity}× {line.description}
            </span>
            <span className="tabular-nums text-gray-600">
              {euro(lineGross(line.line_extension_amount, line.line_tax_total), receipt.currency)}
            </span>
          </label>
        ))}
      </div>

      <label className="mt-3 flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" checked={full} onChange={(e) => setFull(e.target.checked)} />
        Full refund (all items)
      </label>

      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium text-gray-700">Reason</span>
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand"
        />
      </label>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {warning && <p className="mt-3 text-sm text-amber-700">{warning}</p>}

      <div className="mt-4">
        <Button onClick={submit} disabled={busy}>
          <PiArrowUDownLeft /> {busy ? "Creating…" : "Create credit note"}
        </Button>
      </div>
    </Card>
  );
}
