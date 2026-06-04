// Typed API client. One axios instance with cookies enabled (for the optional
// account/JWT). Receipts are public, so a 401 is NOT a redirect — it just means
// "not logged in", which the UI handles by showing the account-gated actions as
// a login prompt.
import axios from "axios";

export const http = axios.create({
  baseURL: "/api",
  withCredentials: true, // send the optional auth cookie when present
});

// Pull a human-readable message out of a FastAPI error response.
export function apiError(err: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

// ---- Types ----
export type Channel = "NFC" | "ONLINE_LINK";
export type ReceiptStatus = "GENERATED" | "VIEWED" | "SENT" | "REFUNDED";
export type CreditNoteStatus = "GENERATED" | "SENT";

// Money fields arrive as strings (Decimal); the format helpers accept both.
type Money = string | number;

export interface InvoiceLine {
  id: number;
  description: string;
  quantity: number;
  unit_price: Money;
  vat_rate: Money;
  line_extension_amount: Money;
  line_tax_total: Money;
}

export interface Receipt {
  invoice_id: string;
  issue_date: string;
  issue_time: string;
  currency: string;
  channel: Channel;
  supplier_name: string;
  supplier_vat: string | null;
  supplier_address: string;
  supplier_country: string;
  buyer_name: string;
  buyer_email: string | null;
  invoice_lines: InvoiceLine[];
  line_extension_amount: Money;
  tax_exclusive_amount: Money;
  tax_inclusive_amount: Money;
  payable_amount: Money;
  tax_total: Money;
  delivery_url: string;
  status: ReceiptStatus;
  sent_to_user_email: string | null;
  sent_to_accountant_email: string | null;
  sent_at: string | null;
  credit_note_id: string | null;
  created_at: string;
}

export interface CreditNote {
  credit_note_id: string;
  original_receipt_id: string;
  issue_date: string;
  issue_time: string;
  currency: string;
  credited_items: InvoiceLine[];
  line_extension_amount: Money;
  tax_exclusive_amount: Money;
  tax_inclusive_amount: Money;
  payable_amount: Money;
  tax_total: Money;
  reason: string;
  status: CreditNoteStatus;
  sent_to_user_email: string | null;
  sent_to_accountant_email: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface BasketLinePreview {
  description: string;
  quantity: number;
  unit_price: string;
  vat_rate: string;
}
export interface DemoBasket {
  name: string;
  vat: string;
  address: string;
  default_channel: Channel;
  lines: BasketLinePreview[];
  preview_total: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  accountant_email: string | null;
  created_at: string;
}

// ---- Account (optional) ----
export async function register(body: {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  accountant_email?: string | null;
}): Promise<User> {
  const { data } = await http.post<User>("/register", body);
  return data;
}

export async function login(email: string, password: string): Promise<void> {
  // The backend uses an OAuth2 form (username = email).
  const form = new URLSearchParams({ username: email, password });
  await http.post("/login", form);
}

export async function logout(): Promise<void> {
  await http.post("/logout");
}

export async function getMe(): Promise<User> {
  const { data } = await http.get<User>("/me");
  return data;
}

export async function updateMe(body: {
  first_name?: string;
  last_name?: string;
  accountant_email?: string | null;
}): Promise<User> {
  const { data } = await http.put<User>("/me", body);
  return data;
}

// ---- Checkout (the merchant source) ----
export async function getDemoBaskets(): Promise<Record<string, DemoBasket>> {
  const { data } = await http.get<Record<string, DemoBasket>>("/checkout/demo-baskets");
  return data;
}

export async function checkout(merchant_key: string, channel: Channel): Promise<Receipt> {
  const { data } = await http.post<Receipt>("/checkout", { merchant_key, channel });
  return data;
}

// ---- Receipts ----
export async function listReceipts(mine = false): Promise<Receipt[]> {
  const { data } = await http.get<Receipt[]>("/receipts", { params: mine ? { mine: true } : {} });
  return data;
}

export async function getReceipt(id: string): Promise<Receipt> {
  const { data } = await http.get<Receipt>(`/receipts/${id}`);
  return data;
}

export async function emailReceiptToSelf(id: string): Promise<{ detail: string }> {
  const { data } = await http.post(`/receipts/${id}/email`, {});
  return data;
}

export async function sendToAccountant(id: string): Promise<{ detail: string }> {
  const { data } = await http.post(`/receipts/${id}/send-to-accountant`);
  return data;
}

// ---- Refund / credit note ----
export async function refundReceipt(
  id: string,
  body: { full?: boolean; line_ids?: number[]; reason?: string }
): Promise<{ credit_note: CreditNote; warning: string | null }> {
  const { data } = await http.post(`/receipts/${id}/refund`, body);
  return data;
}

export async function getCreditNote(id: string): Promise<CreditNote> {
  const { data } = await http.get<CreditNote>(`/credit-notes/${id}`);
  return data;
}

// ---- Download URLs (hit the proxied API; the cookie rides along) ----
export const pdfUrl = (id: string) => `/api/receipts/${id}/pdf`;
export const pngUrl = (id: string) => `/api/receipts/${id}/png`;
export const jsonUrl = (id: string) => `/api/receipts/${id}/json`;
export const ublUrl = (id: string) => `/api/receipts/${id}/ubl`;
export const creditNotePdfUrl = (id: string) => `/api/credit-notes/${id}/pdf`;
export const creditNotePngUrl = (id: string) => `/api/credit-notes/${id}/png`;
export const creditNoteJsonUrl = (id: string) => `/api/credit-notes/${id}/json`;
export const creditNoteUblUrl = (id: string) => `/api/credit-notes/${id}/ubl`;
