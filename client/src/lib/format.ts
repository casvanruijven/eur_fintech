// Small formatting helpers. Money fields arrive as Decimal strings from the API,
// so everything funnels through Number() before display.

export function euro(amount: string | number, currency = "EUR"): string {
  const n = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-IE", { style: "currency", currency }).format(
    Number.isFinite(n) ? n : 0
  );
}

export function vatPct(rate: string | number): string {
  const n = typeof rate === "string" ? parseFloat(rate) : rate;
  return `${Math.round(n * 100)}%`;
}

export function lineGross(net: string | number, tax: string | number): number {
  const n = typeof net === "string" ? parseFloat(net) : net;
  const t = typeof tax === "string" ? parseFloat(tax) : tax;
  return n + t;
}

export function channelLabel(channel: string): string {
  return channel === "NFC" ? "NFC tap" : channel === "ONLINE_LINK" ? "Online link" : channel;
}
