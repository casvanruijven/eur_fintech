// The visual receipt — a clean, browser-native render of the structured data.
// This is what the customer sees the instant they tap the NFC tile or open the
// online link (no app, no scanning).
import type { Receipt } from "../api";
import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";
import { euro, lineGross, vatPct } from "../lib/format";

export function ReceiptDocument({ receipt }: { receipt: Receipt }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-gray-100 bg-brand/5 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-gray-900">{receipt.supplier_name}</div>
            {receipt.supplier_vat && (
              <div className="text-sm text-gray-500">VAT {receipt.supplier_vat}</div>
            )}
            <div className="text-sm text-gray-500">{receipt.supplier_address}</div>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <StatusBadge value={receipt.channel} kind="channel" />
            <StatusBadge value={receipt.status} />
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="font-mono font-medium text-gray-700">{receipt.invoice_id}</span>
          <span className="text-gray-500">
            {receipt.issue_date} {receipt.issue_time}
          </span>
        </div>
      </div>

      <div className="px-5 py-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="pb-2 font-medium">Item</th>
              <th className="pb-2 text-center font-medium">Qty</th>
              <th className="pb-2 text-right font-medium">VAT</th>
              <th className="pb-2 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {receipt.invoice_lines.map((line) => (
              <tr key={line.id}>
                <td className="py-2 text-gray-800">{line.description}</td>
                <td className="py-2 text-center text-gray-500">{line.quantity}</td>
                <td className="py-2 text-right text-gray-500">{vatPct(line.vat_rate)}</td>
                <td className="py-2 text-right tabular-nums text-gray-800">
                  {euro(lineGross(line.line_extension_amount, line.line_tax_total), receipt.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 space-y-1 border-t border-gray-100 pt-3 text-sm">
          <Row label="Subtotal (excl. VAT)" value={euro(receipt.line_extension_amount, receipt.currency)} />
          <Row label="VAT" value={euro(receipt.tax_total, receipt.currency)} />
          <Row
            label="Total"
            value={euro(receipt.payable_amount, receipt.currency)}
            strong
          />
        </div>

        {receipt.credit_note_id && (
          <div className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            Linked credit note: <span className="font-mono">{receipt.credit_note_id}</span>
          </div>
        )}
        {receipt.sent_at && (
          <div className="mt-2 text-xs text-gray-400">
            {receipt.sent_to_accountant_email
              ? `Sent to accountant ${receipt.sent_to_accountant_email}`
              : `Emailed to ${receipt.sent_to_user_email}`}
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "text-base font-semibold text-gray-900" : "text-gray-600"}`}>
      <span>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}
