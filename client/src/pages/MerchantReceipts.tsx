// Merchant dashboard — every receipt generated through ZZPay, with its status.
// Useful for the demo (and a hook for the future merchant portal / support log).
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as api from "../api";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";
import { StatusBadge } from "../components/StatusBadge";
import { euro } from "../lib/format";

export function MerchantReceipts() {
  const { data: receipts, isLoading } = useQuery({
    queryKey: ["receipts", "all"],
    queryFn: () => api.listReceipts(false),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Generated receipts</h1>
        <p className="mt-1 text-gray-600">All receipts created through ZZPay, with status.</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <Spinner className="text-3xl" />
        </div>
      ) : !receipts?.length ? (
        <Card className="p-6 text-center text-gray-600">
          No receipts yet — generate one from the{" "}
          <Link to="/merchant" className="text-brand underline">
            merchant
          </Link>{" "}
          or{" "}
          <Link to="/online-checkout" className="text-brand underline">
            online checkout
          </Link>{" "}
          demo.
        </Card>
      ) : (
        <Card className="divide-y divide-gray-100">
          {receipts.map((r) => (
            <Link
              key={r.invoice_id}
              to={`/receipt/${r.invoice_id}`}
              className="flex items-center justify-between px-5 py-3 hover:bg-gray-50"
            >
              <div>
                <div className="font-mono text-sm font-medium text-gray-900">{r.invoice_id}</div>
                <div className="text-sm text-gray-500">
                  {r.supplier_name} · {r.issue_date}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge value={r.channel} kind="channel" />
                <StatusBadge value={r.status} />
                <span className="w-20 text-right tabular-nums text-sm font-medium text-gray-800">
                  {euro(r.payable_amount, r.currency)}
                </span>
              </div>
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}
