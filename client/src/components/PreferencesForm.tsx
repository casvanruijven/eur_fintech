// Browser-local preferences (no account). Remembers a returning visitor's name,
// own email and preferred export format on THIS device — the "no account required"
// convenience layer. The accountant email is intentionally NOT here; that lives in
// the account so it can drive server-side forwarding.
import { useState } from "react";
import { PiFloppyDisk, PiTrash } from "react-icons/pi";
import { Button } from "./Button";
import { Card } from "./Card";
import { Input } from "./Input";
import {
  clearPrefs,
  getPrefs,
  hasRemembered,
  savePrefs,
  type ExportFormat,
} from "../lib/storage-service";

const FORMATS: ExportFormat[] = ["pdf", "png", "json", "ubl"];

export function PreferencesForm() {
  // Read once via initializer (avoids re-reading localStorage on every render).
  const [prefs, setPrefs] = useState(() => getPrefs());
  const [remembered, setRemembered] = useState(() => hasRemembered());
  const [saved, setSaved] = useState(false);

  function save() {
    setPrefs(savePrefs(prefs));
    setRemembered(true);
    setSaved(true);
  }

  function clear() {
    clearPrefs();
    setPrefs(getPrefs());
    setRemembered(false);
    setSaved(false);
  }

  return (
    <Card className="p-5">
      <h3 className="text-base font-semibold text-gray-900">This browser</h3>
      <p className="mt-1 text-sm text-gray-500">
        Saved locally on this device — no account needed.
      </p>
      {remembered && (
        <div className="mt-3 rounded-lg bg-brand/5 px-3 py-2 text-sm text-brand">
          We remembered your details on this browser. No account required.
        </div>
      )}

      <div className="mt-4 space-y-3">
        <Input
          label="Name"
          value={prefs.name}
          onChange={(e) => setPrefs({ ...prefs, name: e.target.value })}
        />
        <Input
          label="Your email"
          type="email"
          value={prefs.userEmail}
          onChange={(e) => setPrefs({ ...prefs, userEmail: e.target.value })}
        />
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">
            Preferred export format
          </span>
          <select
            value={prefs.preferredFormat}
            onChange={(e) =>
              setPrefs({ ...prefs, preferredFormat: e.target.value as ExportFormat })
            }
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand"
          >
            {FORMATS.map((f) => (
              <option key={f} value={f}>
                {f.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={save}>
          <PiFloppyDisk /> Remember my details
        </Button>
        <Button variant="secondary" onClick={clear}>
          <PiTrash /> Clear local preferences
        </Button>
      </div>
      {saved && <p className="mt-2 text-sm text-green-700">Saved on this browser.</p>}
    </Card>
  );
}
