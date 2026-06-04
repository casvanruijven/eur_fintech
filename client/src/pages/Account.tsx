import { useState, type FormEvent } from "react";
import * as api from "../api";
import { apiError } from "../api";
import { useAuth } from "../auth";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";

export function Account() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    accountant_email: user?.accountant_email ?? "",
  });
  const [flash, setFlash] = useState("");
  const [busy, setBusy] = useState(false);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFlash("");
    setBusy(true);
    try {
      await api.updateMe({
        first_name: form.first_name,
        last_name: form.last_name,
        accountant_email: form.accountant_email || null,
      });
      await refresh();
      setFlash("Opgeslagen");
    } catch (err) {
      setFlash(apiError(err, "Opslaan mislukt"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Account</h2>
      <Card className="max-w-md p-6">
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Voornaam"
              name="first_name"
              value={form.first_name}
              onChange={(e) => set("first_name", e.target.value)}
            />
            <Input
              label="Achternaam"
              name="last_name"
              value={form.last_name}
              onChange={(e) => set("last_name", e.target.value)}
            />
          </div>
          <div>
            <span className="mb-1 block text-sm font-medium text-gray-700">E-mailadres</span>
            <p className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-500">{user?.email}</p>
          </div>
          <Input
            label="E-mail boekhouder"
            name="accountant_email"
            type="email"
            value={form.accountant_email}
            onChange={(e) => set("accountant_email", e.target.value)}
            placeholder="boekhouder@voorbeeld.nl"
          />
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={busy}>
              {busy ? "Bezig…" : "Opslaan"}
            </Button>
            {flash && <span className="text-sm text-brand">{flash}</span>}
          </div>
        </form>
      </Card>
    </div>
  );
}
