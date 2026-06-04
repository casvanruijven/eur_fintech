// The action bar under a receipt. Reflects the two-tier access model:
//   - anyone: download PDF/PNG, request a refund;
//   - logged-in account: structured JSON/UBL export, email to self, send to
//     accountant (PDF + UBL). Anonymous visitors see a gentle prompt to log in.
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PiEnvelopeSimple, PiPaperPlaneTilt } from "react-icons/pi";
import type { Receipt } from "../api";
import * as api from "../api";
import { useAuth } from "../auth";
import { Button } from "./Button";
import { Card } from "./Card";
import { ExportButtons } from "./ExportButtons";
import { RefundPanel } from "./RefundPanel";
import { euro } from "../lib/format";

export function ReceiptActions({
  receipt,
  onChange,
}: {
  receipt: Receipt;
  onChange: () => void;
}) {
  const { user } = useAuth();
  const loggedIn = !!user;
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function emailSelf() {
    setMsg(null);
    setErr(null);
    setBusy("self");
    try {
      const res = await api.emailReceiptToSelf(receipt.invoice_id);
      setMsg(res.detail);
      onChange();
    } catch (e) {
      setErr(api.apiError(e));
    } finally {
      setBusy(null);
    }
  }

  async function emailAccountant() {
    setMsg(null);
    setErr(null);
    setBusy("acc");
    try {
      const res = await api.sendToAccountant(receipt.invoice_id);
      setMsg(res.detail);
      onChange();
    } catch (e) {
      setErr(api.apiError(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <h3 className="text-base font-semibold text-gray-900">Export</h3>
        <p className="mt-1 text-sm text-gray-500">
          Human-readable PDF/PNG for anyone; structured JSON & EN 16931 UBL e-invoice
          for account holders.
        </p>
        <div className="mt-3">
          <ExportButtons
            urls={{
              pdf: api.pdfUrl(receipt.invoice_id),
              png: api.pngUrl(receipt.invoice_id),
              json: api.jsonUrl(receipt.invoice_id),
              ubl: api.ublUrl(receipt.invoice_id),
            }}
            loggedIn={loggedIn}
            baseName={`zzpay-${receipt.invoice_id}`}
          />
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-base font-semibold text-gray-900">Email</h3>
        {loggedIn ? (
          <>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="secondary" disabled={busy !== null} onClick={emailSelf}>
                <PiEnvelopeSimple /> Email to myself
              </Button>
              <Button disabled={busy !== null} onClick={emailAccountant}>
                <PiPaperPlaneTilt /> Send to accountant (PDF + UBL)
              </Button>
            </div>
            {!user?.accountant_email && (
              <p className="mt-2 text-xs text-gray-400">
                Set an accountant email on your{" "}
                <Link to="/account" className="text-brand underline">
                  account page
                </Link>{" "}
                to enable accountant forwarding.
              </p>
            )}
          </>
        ) : (
          <p className="mt-2 text-sm text-gray-500">
            <Link to="/account" className="text-brand underline">
              Log in or create a free account
            </Link>{" "}
            to email this receipt to yourself or your accountant.
          </p>
        )}
        {msg && <p className="mt-3 text-sm text-green-700">{msg}</p>}
        {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
      </Card>

      {receipt.credit_note_id ? (
        <CreditNoteSection creditNoteId={receipt.credit_note_id} loggedIn={loggedIn} />
      ) : (
        <RefundPanel receipt={receipt} onRefunded={onChange} />
      )}
    </div>
  );
}

function CreditNoteSection({ creditNoteId, loggedIn }: { creditNoteId: string; loggedIn: boolean }) {
  const { data: cn } = useQuery({
    queryKey: ["credit-note", creditNoteId],
    queryFn: () => api.getCreditNote(creditNoteId),
  });

  return (
    <Card className="p-5">
      <h3 className="text-base font-semibold text-gray-900">Linked credit note</h3>
      <p className="mt-1 text-sm text-gray-500">
        This receipt was refunded. The original is preserved; the correction lives in a
        separate credit note.
      </p>
      <div className="mt-3 rounded-lg bg-gray-50 px-4 py-3 text-sm">
        <div className="flex justify-between">
          <span className="font-mono font-medium">{creditNoteId}</span>
          {cn && (
            <span className="tabular-nums font-semibold text-red-700">
              − {euro(cn.payable_amount, cn.currency)}
            </span>
          )}
        </div>
        {cn && <div className="mt-1 text-gray-500">Reason: {cn.reason}</div>}
      </div>
      <div className="mt-3">
        <ExportButtons
          urls={{
            pdf: api.creditNotePdfUrl(creditNoteId),
            png: api.creditNotePngUrl(creditNoteId),
            json: api.creditNoteJsonUrl(creditNoteId),
            ubl: api.creditNoteUblUrl(creditNoteId),
          }}
          loggedIn={loggedIn}
          baseName={`zzpay-${creditNoteId}`}
        />
      </div>
    </Card>
  );
}
