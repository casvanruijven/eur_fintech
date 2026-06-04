import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { PiArrowLeft, PiDownloadSimple, PiEnvelopeSimple, PiImage } from "react-icons/pi";
import * as api from "../api";
import { apiError } from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";

function euro(amount: string | number, currency: string) {
  return `${currency} ${Number(amount).toFixed(2)}`;
}

export function ReceiptDetail() {
  const { id = "" } = useParams();
  const [flash, setFlash] = useState("");

  const { data: receipt, isLoading } = useQuery({
    queryKey: ["receipt", id],
    queryFn: () => api.getReceipt(id),
  });

  const email = useMutation({
    mutationFn: (target: "self" | "accountant") => api.emailReceipt(id, target),
    onSuccess: (res) => setFlash(res.detail),
    onError: (err) => setFlash(apiError(err, "Versturen mislukt")),
  });

  if (isLoading || !receipt) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="text-3xl" />
      </div>
    );
  }

  return (
    <div>
      <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
        <PiArrowLeft /> Terug naar overzicht
      </Link>

      <Card className="p-6">
        <h2 className="text-xl font-semibold">{receipt.merchant_name}</h2>
        {receipt.merchant_vat && (
          <p className="text-sm text-gray-500">BTW: {receipt.merchant_vat}</p>
        )}
        <p className="text-sm text-gray-500">
          {new Date(receipt.purchased_at).toLocaleString("nl-NL")}
        </p>

        <div className="my-4 border-t border-dashed border-gray-200" />

        <ul className="space-y-1 text-sm">
          {receipt.line_items.map((item, i) => (
            <li key={i} className="flex justify-between">
              <span>
                {item.quantity}× {item.description}
              </span>
              <span>{euro(item.unit_price, receipt.currency)}</span>
            </li>
          ))}
        </ul>

        <div className="my-4 border-t border-dashed border-gray-200" />

        <div className="space-y-1 text-sm">
          <div className="flex justify-between text-gray-500">
            <span>BTW</span>
            <span>{euro(receipt.vat_amount, receipt.currency)}</span>
          </div>
          <div className="flex justify-between text-base font-semibold">
            <span>Totaal</span>
            <span>{euro(receipt.total_amount, receipt.currency)}</span>
          </div>
        </div>
      </Card>

      <div className="mt-4 flex flex-wrap gap-2">
        <a href={api.pdfUrl(receipt.id)} download>
          <Button variant="secondary">
            <PiDownloadSimple /> PDF
          </Button>
        </a>
        <a href={api.pngUrl(receipt.id)} download>
          <Button variant="secondary">
            <PiImage /> PNG
          </Button>
        </a>
        <Button onClick={() => email.mutate("self")} disabled={email.isPending}>
          <PiEnvelopeSimple /> Mail naar mij
        </Button>
        <Button
          variant="secondary"
          onClick={() => email.mutate("accountant")}
          disabled={email.isPending}
        >
          <PiEnvelopeSimple /> Mail naar boekhouder
        </Button>
      </div>

      {flash && <p className="mt-3 text-sm text-brand">{flash}</p>}
    </div>
  );
}
