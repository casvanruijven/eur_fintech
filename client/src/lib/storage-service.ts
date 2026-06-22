// Browser-local preferences (no account required).
//
// Per the MVP design: the *accountant* email and structured-export rights live in
// the optional account (server-side). This light localStorage layer just remembers
// a returning visitor's name / own email / preferred download format on THIS
// browser, so we can prefill fields and show "we remembered your details here".
//
// In production this would be replaced by secure, authenticated profile storage.

const KEY = "zzpay.prefs.v1";

export type ExportFormat = "pdf" | "png" | "json" | "ubl";

export interface Prefs {
  name: string;
  userEmail: string;
  preferredFormat: ExportFormat;
  remembered: boolean;
}

const DEFAULT_PREFS: Prefs = {
  name: "",
  userEmail: "",
  preferredFormat: "pdf",
  remembered: false,
};

export function getPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    return { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<Prefs>) };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function savePrefs(prefs: Partial<Prefs>): Prefs {
  const next = { ...getPrefs(), ...prefs, remembered: true };
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage disabled (private mode) — preferences just won't persist */
  }
  return next;
}

export function clearPrefs(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export function hasRemembered(): boolean {
  return getPrefs().remembered;
}

// --------------------------------------------------------------------------- //
// Recent receipts on THIS device (so the demo/anonymous user can find receipts
// they just generated or opened, without exposing anyone else's). Most-recent
// first, capped. This is device memory, not an account.
// --------------------------------------------------------------------------- //
const RECENT_KEY = "zzpay.recent.v1";
const RECENT_MAX = 20;

export function addRecentReceipt(invoiceId: string): void {
  try {
    const existing = getRecentReceipts().filter((id) => id !== invoiceId);
    const next = [invoiceId, ...existing].slice(0, RECENT_MAX);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

export function getRecentReceipts(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function removeRecentReceipt(invoiceId: string): void {
  try {
    const next = getRecentReceipts().filter((id) => id !== invoiceId);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}
