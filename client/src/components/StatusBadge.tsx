// A small pill for a receipt/credit-note status, or a delivery channel.
import { channelLabel } from "../lib/format";

const STATUS_STYLES: Record<string, string> = {
  GENERATED: "bg-gray-100 text-gray-700",
  VIEWED: "bg-blue-100 text-blue-700",
  SENT: "bg-amber-100 text-amber-800",
  REFUNDED: "bg-red-100 text-red-700",
};

const CHANNEL_STYLE = "bg-brand/10 text-brand";

export function StatusBadge({
  value,
  kind = "status",
}: {
  value: string;
  kind?: "status" | "channel";
}) {
  const label = kind === "channel" ? channelLabel(value) : value;
  const style = kind === "channel" ? CHANNEL_STYLE : STATUS_STYLES[value] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}
