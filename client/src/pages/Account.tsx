// Account & preferences. The account is OPTIONAL: it stores the accountant email
// (for forwarding) and remembers a returning user via the JWT cookie, which is what
// unlocks the structured-export + email actions on a receipt. Anonymous visitors can
// still view and download PDF/PNG everywhere.
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PiSignOut, PiReceipt } from "react-icons/pi";
import * as api from "../api";
import { useAuth } from "../auth";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { StatusBadge } from "../components/StatusBadge";
import { PreferencesForm } from "../components/PreferencesForm";
import { euro } from "../lib/format";

export function Account() {
  const { user, loading } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Account & preferences</h1>
        <p className="mt-1 text-gray-600">
          An account is optional. It remembers your accountant and lets you export the
          structured e-invoice and email receipts. Viewing & PDF/PNG never need one.
        </p>
      </div>

      {loading ? null : user ? <LoggedIn /> : <LoggedOut />}

      <PreferencesForm />
    </div>
  );
}

function LoggedIn() {
  const { user, logout, refresh } = useAuth();
  const [accountant, setAccountant] = useState(user?.accountant_email ?? "");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: mine } = useQuery({
    queryKey: ["receipts", "mine"],
    queryFn: () => api.listReceipts(true),
  });

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      await api.updateMe({ accountant_email: accountant || null });
      await refresh();
      setMsg("Saved.");
    } catch (e) {
      setMsg(api.apiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Card className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              {user?.first_name} {user?.last_name}
            </h3>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
          <Button variant="secondary" onClick={() => void logout()}>
            <PiSignOut /> Log out
          </Button>
        </div>

        <div className="mt-4 space-y-3">
          <Input
            label="Accountant email (used by 'Send to accountant')"
            type="email"
            placeholder="accountant@demo-accounting.nl"
            value={accountant}
            onChange={(e) => setAccountant(e.target.value)}
          />
          <Button onClick={save} disabled={busy}>
            Save accountant
          </Button>
          {msg && <p className="text-sm text-green-700">{msg}</p>}
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-base font-semibold text-gray-900">My expenses</h3>
        <p className="mt-1 text-sm text-gray-500">
          Receipts you've exported or emailed are linked to your account.
        </p>
        {!mine?.length ? (
          <p className="mt-3 text-sm text-gray-500">
            None yet — open a receipt and export or email it to link it here.
          </p>
        ) : (
          <div className="mt-3 divide-y divide-gray-100">
            {mine.map((r) => (
              <Link
                key={r.invoice_id}
                to={`/receipt/${r.invoice_id}`}
                className="flex items-center justify-between py-2 hover:bg-gray-50"
              >
                <span className="flex items-center gap-2 text-sm">
                  <PiReceipt className="text-gray-400" />
                  <span className="font-mono">{r.invoice_id}</span>
                  <span className="text-gray-500">{r.supplier_name}</span>
                </span>
                <span className="flex items-center gap-2">
                  <StatusBadge value={r.status} />
                  <span className="tabular-nums text-sm">{euro(r.payable_amount, r.currency)}</span>
                </span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}

function LoggedOut() {
  const { login, refresh } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    accountant_email: "",
  });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register({
          email: form.email,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
          accountant_email: form.accountant_email || null,
        });
      }
      await login(form.email, form.password);
      await refresh();
    } catch (e2) {
      setErr(api.apiError(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="mb-4 flex gap-2 text-sm">
        <button
          onClick={() => setMode("login")}
          className={mode === "login" ? "font-semibold text-brand" : "text-gray-500"}
        >
          Log in
        </button>
        <span className="text-gray-300">·</span>
        <button
          onClick={() => setMode("register")}
          className={mode === "register" ? "font-semibold text-brand" : "text-gray-500"}
        >
          Create account
        </button>
      </div>

      <p className="mb-4 rounded-lg bg-brand/5 px-3 py-2 text-sm text-gray-600">
        Demo account: <span className="font-mono">demo@zzpay.nl</span> /{" "}
        <span className="font-mono">demo1234</span>
      </p>

      <form onSubmit={submit} className="space-y-3">
        {mode === "register" && (
          <div className="grid grid-cols-2 gap-3">
            <Input label="First name" value={form.first_name} onChange={set("first_name")} required />
            <Input label="Last name" value={form.last_name} onChange={set("last_name")} required />
          </div>
        )}
        <Input label="Email" type="email" value={form.email} onChange={set("email")} required />
        <Input
          label="Password"
          type="password"
          value={form.password}
          onChange={set("password")}
          required
          minLength={8}
        />
        {mode === "register" && (
          <Input
            label="Accountant email (optional)"
            type="email"
            value={form.accountant_email}
            onChange={set("accountant_email")}
          />
        )}
        {err && <p className="text-sm text-red-600">{err}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? "…" : mode === "login" ? "Log in" : "Create account & log in"}
        </Button>
      </form>
    </Card>
  );
}
