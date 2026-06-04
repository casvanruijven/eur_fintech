// Flow 2 — online checkout / multi-channel simulation.
// Same receipt model as the NFC flow, delivered through an online link instead of
// a tile. Demonstrates that NFC is just one delivery channel.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PiGlobeSimple, PiCheckCircle, PiReceipt } from "react-icons/pi";
import * as api from "../api";
import type { Receipt } from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";
import { euro, vatPct } from "../lib/format";

const MERCHANT_KEY = "shell";

export function OnlineCheckout() {
  const navigate = useNavigate();
  const { data: baskets } = useQuery({ queryKey: ["demo-baskets"], queryFn: api.getDemoBaskets });
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const basket = baskets?.[MERCHANT_KEY];

  async function placeOrder() {
    setErr(null);
    setBusy(true);
    try {
      setReceipt(await api.checkout(MERCHANT_KEY, "ONLINE_LINK"));
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
        <h1 className="text-2xl font-bold text-gray-900">Online checkout</h1>
        <p className="mt-1 text-gray-600">
          {basket.name} · webshop simulation. NFC is only one delivery channel — the same
          structured receipt is delivered here through an online link.
        </p>
      </div>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <div className="font-semibold text-gray-900">{basket.name}</div>
          <span className="inline-flex items-center gap-1 rounded-full bg-brand/10 px-2.5 py-0.5 text-xs font-semibold text-brand">
            <PiGlobeSimple /> Online checkout
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
          <Button onClick={placeOrder} disabled={busy || !!receipt}>
            <PiGlobeSimple /> {busy ? "Placing order…" : "Place order & pay"}
          </Button>
        </div>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </Card>

      {receipt && (
        <Card className="border-brand/30 bg-brand/5 p-5 text-center">
          <PiCheckCircle className="mx-auto text-3xl text-brand" />
          <h2 className="mt-2 text-lg font-semibold text-gray-900">Thank you for your order!</h2>
          <p className="mt-1 text-sm text-gray-600">
            Your ZZPay receipt <span className="font-mono">{receipt.invoice_id}</span> is ready.
          </p>
          <div className="mt-4">
            <Button onClick={() => navigate(receipt.delivery_url)}>
              <PiReceipt /> View your ZZPay receipt
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
