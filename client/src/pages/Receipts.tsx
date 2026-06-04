import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PiPlus, PiReceipt } from "react-icons/pi";
import * as api from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Spinner } from "../components/Spinner";

function euro(amount: string, currency: string) {
  return `${currency} ${Number(amount).toFixed(2)}`;
}

// A prefilled mock receipt — stands in for a real merchant NFC tap in the MVP.
function mockReceipt(): api.ReceiptCreate {
  return {
    merchant_name: "Demo Winkel",
    purchased_at: new Date().toISOString(),
    total_amount: "9.95",
    vat_amount: "0.90",
    line_items: [{ description: "Demo product", quantity: 1, unit_price: "9.95" }],
  };
}

export function Receipts() {
  const queryClient = useQueryClient();
  const { data: receipts, isLoading } = useQuery({
    queryKey: ["receipts"],
    queryFn: api.listReceipts,
  });

  const createMock = useMutation({
    mutationFn: () => api.createReceipt(mockReceipt()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["receipts"] }),
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Mijn kassabonnen</h2>
        <Button
          variant="secondary"
          onClick={() => createMock.mutate()}
          disabled={createMock.isPending}
        >
          <PiPlus /> Demo-bon toevoegen
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="text-3xl" />
        </div>
      ) : !receipts?.length ? (
        <Card className="p-8 text-center text-gray-500">
          <PiReceipt className="mx-auto mb-2 text-3xl text-gray-400" />
          Nog geen bonnen. Voeg een demo-bon toe om te beginnen.
        </Card>
      ) : (
        <ul className="space-y-2">
          {receipts.map((r) => (
            <li key={r.id}>
              <Link to={`/receipts/${r.id}`}>
                <Card className="flex items-center justify-between p-4 hover:border-brand">
                  <div>
                    <p className="font-medium">{r.merchant_name}</p>
                    <p className="text-sm text-gray-500">
                      {new Date(r.purchased_at).toLocaleDateString("nl-NL", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <span className="font-semibold">{euro(r.total_amount, r.currency)}</span>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
