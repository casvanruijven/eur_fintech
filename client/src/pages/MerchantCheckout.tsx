// Flow 1 — physical checkout via NFC simulation.
// The cashier sees the basket, clicks "Generate ZZPay Receipt", and gets a receipt
// ready for the NFC tile. "Simulate customer tap" stands in for the real tap and
// opens the public receipt page.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PiCreditCard, PiHandTap, PiCheckCircle } from "react-icons/pi";
import * as api from "../api";
import type { Receipt } from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";
import { euro, vatPct } from "../lib/format";
import { addRecentReceipt } from "../lib/storage-service";

const MERCHANT_KEY = "bouwmaat";

export function MerchantCheckout() {
  const navigate = useNavigate();
  const { data: baskets } = useQuery({ queryKey: ["demo-baskets"], queryFn: api.getDemoBaskets });
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const basket = baskets?.[MERCHANT_KEY];

  async function generate() {
    setErr(null);
    setBusy(true);
    try {
      const r = await api.checkout(MERCHANT_KEY, "NFC");
      addRecentReceipt(r.invoice_id);
      setReceipt(r);
    } catch (e) {
      setErr(api.apiError(e));
    } finally {
      setBusy(false);
    }
  }

  if (!basket) {
    return (
      <div className="flex justify-center py-10">
        <Spinner className="text-3xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Merchant checkout</h1>
        <p className="mt-1 text-gray-600">
          {basket.name} · register simulation. In production this is the merchant's
          point-of-sale; here it's a button.
        </p>
      </div>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold text-gray-900">{basket.name}</div>
            <div className="text-sm text-gray-500">
              VAT {basket.vat} · {basket.address}
            </div>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-brand/10 px-2.5 py-0.5 text-xs font-semibold text-brand">
            <PiCreditCard /> NFC checkout
          </span>
        </div>

        <table className="mt-4 w-full text-sm">
          <tbody className="divide-y divide-gray-100">
            {basket.lines.map((line, i) => (
              <tr key={i}>
                <td className="py-2 text-gray-800">{line.description}</td>
                <td className="py-2 text-center text-gray-500">{line.quantity}×</td>
                <td className="py-2 text-right text-gray-500">incl. {vatPct(line.vat_rate)}</td>
                <td className="py-2 text-right tabular-nums text-gray-800">
                  {euro(Number(line.unit_price) * line.quantity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-3 flex justify-between border-t border-gray-100 pt-3 text-base font-semibold">
          <span>Total</span>
          <span className="tabular-nums">{euro(basket.preview_total)}</span>
        </div>

        <div className="mt-5">
          <Button onClick={generate} disabled={busy || !!receipt}>
            <PiCreditCard /> {busy ? "Generating…" : "Generate ZZPay Receipt"}
          </Button>
        </div>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </Card>

      {receipt && (
        <Card className="border-brand/30 bg-brand/5 p-5">
          <div className="flex items-center gap-2 text-brand">
            <PiCheckCircle className="text-xl" />
            <h2 className="text-lg font-semibold">Receipt is ready for the NFC tile</h2>
          </div>
          <dl className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Receipt ID</dt>
              <dd className="font-mono font-medium">{receipt.invoice_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">NFC URL</dt>
              <dd className="font-mono text-gray-700">{receipt.delivery_url}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-gray-500">
            In production the NFC tile would carry this URL. In the MVP, the tap is a
            button.
          </p>
          <div className="mt-4">
            <Button onClick={() => navigate(receipt.delivery_url)}>
              <PiHandTap /> Simulate customer tap
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
