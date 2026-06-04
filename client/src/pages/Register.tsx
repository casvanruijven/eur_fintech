import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import * as api from "../api";
import { apiError } from "../api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";

export function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    accountant_email: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        accountant_email: form.accountant_email || null,
      });
      // Log straight in after registering.
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(apiError(err, "Registreren mislukt"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm p-6">
        <h1 className="mb-1 text-2xl font-bold text-brand">Account aanmaken</h1>
        <p className="mb-6 text-sm text-gray-500">
          Zo kunnen we je bonnen automatisch naar je mailen.
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Voornaam"
              name="first_name"
              value={form.first_name}
              onChange={(e) => set("first_name", e.target.value)}
              required
            />
            <Input
              label="Achternaam"
              name="last_name"
              value={form.last_name}
              onChange={(e) => set("last_name", e.target.value)}
              required
            />
          </div>
          <Input
            label="E-mailadres"
            name="email"
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            required
          />
          <Input
            label="Wachtwoord (min. 8 tekens)"
            name="password"
            type="password"
            minLength={8}
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            required
          />
          <Input
            label="E-mail boekhouder (optioneel)"
            name="accountant_email"
            type="email"
            value={form.accountant_email}
            onChange={(e) => set("accountant_email", e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Bezig…" : "Account aanmaken"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-500">
          Al een account?{" "}
          <Link to="/login" className="font-medium text-brand hover:underline">
            Inloggen
          </Link>
        </p>
      </Card>
    </div>
  );
}
