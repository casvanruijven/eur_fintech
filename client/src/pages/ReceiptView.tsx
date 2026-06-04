// Flow 3 — the public receipt page. No login, no app: opening this URL (from an
// NFC tap or an online link) shows the receipt immediately, with export / email /
// refund actions. This is the most important screen in the product.
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api";
import { ReceiptDocument } from "../components/ReceiptDocument";
import { ReceiptActions } from "../components/ReceiptActions";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";
import { addRecentReceipt } from "../lib/storage-service";

export function ReceiptView() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const { data: receipt, isLoading, isError } = useQuery({
    queryKey: ["receipt", id],
    queryFn: () => api.getReceipt(id),
  });

  // Remember on this device so the visitor can find it again under "My receipts"
  // even without an account.
  useEffect(() => {
    if (id) addRecentReceipt(id);
  }, [id]);

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["receipt", id] });
    void queryClient.invalidateQueries({ queryKey: ["credit-note"] });
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Spinner className="text-3xl" />
      </div>
    );
  }

  if (isError || !receipt) {
    return (
      <Card className="p-6 text-center text-gray-600">
        Receipt <span className="font-mono">{id}</span> was not found.
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Your receipt</h1>
        <p className="mt-1 text-sm text-gray-500">
          Opened straight in your browser — no app, no account needed.
        </p>
      </div>
      <ReceiptDocument receipt={receipt} />
      <ReceiptActions receipt={receipt} onChange={refresh} />
    </div>
  );
}
