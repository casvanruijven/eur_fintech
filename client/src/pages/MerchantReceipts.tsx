// "My receipts" — privacy-scoped. A logged-in account sees its own receipts; an
// anonymous visitor sees only the receipts opened/generated on THIS device
// (remembered in localStorage). Nobody ever sees another user's receipts.
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PiTrash } from "react-icons/pi";
import type { Receipt } from "../api";
import * as api from "../api";
import { useAuth } from "../auth";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";
import { StatusBadge } from "../components/StatusBadge";
import { euro } from "../lib/format";
import { getRecentReceipts, removeRecentReceipt } from "../lib/storage-service";

export function MerchantReceipts() {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const recentIds = getRecentReceipts();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function dropFromCache(invoiceId: string) {
    // Update every cached receipt list immediately so the row disappears now,
    // instead of waiting for (or depending on) a refetch.
    queryClient.setQueriesData<Receipt[]>({ queryKey: ["receipts"] }, (old) =>
      old ? old.filter((r) => r.invoice_id !== invoiceId) : old
    );
  }

  async function handleDelete(invoiceId: string) {
    if (!window.confirm(`Delete receipt ${invoiceId}? This cannot be undone.`)) return;
    setError(null);
    setBusyId(invoiceId);
    try {
      // Logged-in accounts delete the receipt server-side; anonymous visitors just
      // forget it on this device (they don't own the public receipt).
      if (user) await api.deleteReceipt(invoiceId);
      removeRecentReceipt(invoiceId);
      dropFromCache(invoiceId);
      await queryClient.invalidateQueries({ queryKey: ["receipts"] });
    } catch (e) {
      setError(api.apiError(e, "Could not delete the receipt"));
    } finally {
      setBusyId(null);
    }
  }

  const account = useQuery({
    queryKey: ["receipts", "mine"],
    queryFn: api.listReceipts,
    enabled: !!user,
  });

  const device = useQuery({
    queryKey: ["receipts", "recent", recentIds],
    enabled: !user && !loading && recentIds.length > 0,
    queryFn: async () => {
      const settled = await Promise.allSettled(recentIds.map((id) => api.getReceipt(id)));
      return settled
        .filter((r): r is PromiseFulfilledResult<Receipt> => r.status === "fulfilled")
        .map((r) => r.value);
    },
  });

  const receipts = user ? account.data : device.data;
  const isLoading = loading || (user ? account.isLoading : device.isLoading);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My receipts</h1>
        <p className="mt-1 text-gray-600">
          {user
            ? "Receipts linked to your account."
            : "Receipts you opened on this device. Log in to keep them in your account across devices."}
        </p>
      </div>

      {!user && (
        <Card className="bg-brand/5 p-4 text-sm text-gray-700">
          You're browsing without an account.{" "}
          <Link to="/account" className="text-brand underline">
            Log in or create one
          </Link>{" "}
          to see all your receipts anywhere and export e-invoices.
        </Card>
      )}

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
        <>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Card className="divide-y divide-gray-100">
            {receipts.map((r) => (
              <div key={r.invoice_id} className="flex items-center gap-2 pr-3 hover:bg-gray-50">
                <Link
                  to={`/receipt/${r.invoice_id}`}
                  className="flex flex-1 items-center justify-between px-5 py-3"
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
                <button
                  onClick={() => handleDelete(r.invoice_id)}
                  disabled={busyId === r.invoice_id}
                  title={user ? "Delete from my account" : "Remove from this device"}
                  className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                >
                  <PiTrash />
                </button>
              </div>
            ))}
          </Card>
        </>
      )}
    </div>
  );
}
