// Typed API client. One axios instance with cookies enabled; a 401 interceptor
// bounces the user back to the login page.
import axios from "axios";

export const http = axios.create({
  baseURL: "/api",
  withCredentials: true, // send the httponly auth cookie
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const onAuthPage =
      location.pathname === "/login" || location.pathname === "/register";
    if (err?.response?.status === 401 && !onAuthPage) {
      location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Pull a human-readable message out of a FastAPI error response.
export function apiError(err: unknown, fallback = "Er ging iets mis"): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  }
  return fallback;
}

// ---- Types ----
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  accountant_email: string | null;
  created_at: string;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number | string;
}

export interface Receipt {
  id: string;
  merchant_name: string;
  merchant_vat: string | null;
  purchased_at: string;
  total_amount: string;
  vat_amount: string;
  currency: string;
  line_items: LineItem[];
  created_at: string;
}

export interface ReceiptCreate {
  merchant_name: string;
  merchant_vat?: string | null;
  purchased_at: string;
  total_amount: string;
  vat_amount: string;
  currency?: string;
  line_items?: LineItem[];
}

// ---- Auth ----
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

// ---- Receipts ----
export async function listReceipts(): Promise<Receipt[]> {
  const { data } = await http.get<Receipt[]>("/receipts");
  return data;
}

export async function getReceipt(id: string): Promise<Receipt> {
  const { data } = await http.get<Receipt>(`/receipts/${id}`);
  return data;
}

export async function createReceipt(body: ReceiptCreate): Promise<Receipt> {
  const { data } = await http.post<Receipt>("/receipts", body);
  return data;
}

export async function emailReceipt(
  id: string,
  target: "self" | "accountant"
): Promise<{ detail: string }> {
  const { data } = await http.post(`/receipts/${id}/email`, { target });
  return data;
}

// Download URLs hit the proxied API directly (cookie is sent automatically).
export const pdfUrl = (id: string) => `/api/receipts/${id}/pdf`;
export const pngUrl = (id: string) => `/api/receipts/${id}/png`;
