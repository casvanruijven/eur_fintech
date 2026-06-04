// Export buttons for a receipt or credit note.
//   - PDF / PNG  : public (human-readable) — always available.
//   - JSON / UBL : structured e-invoice — account-gated (a compliant EN 16931
//                  document needs a buyer identity). Shown to everyone, but for
//                  anonymous visitors they prompt to log in instead of failing.
import { useState } from "react";
import { PiFilePdf, PiImage, PiBracketsCurly, PiFileCode } from "react-icons/pi";
import { Button } from "./Button";
import { downloadFile } from "../lib/download";

export interface ExportUrls {
  pdf: string;
  png: string;
  json: string;
  ubl: string;
}

export function ExportButtons({
  urls,
  loggedIn,
  baseName,
}: {
  urls: ExportUrls;
  loggedIn: boolean;
  baseName: string;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(kind: keyof ExportUrls, ext: string) {
    setError(null);
    setBusy(kind);
    try {
      await downloadFile(urls[kind], `${baseName}.${ext}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(null);
    }
  }

  const structuredDisabled = !loggedIn;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy !== null} onClick={() => run("pdf", "pdf")}>
          <PiFilePdf /> PDF
        </Button>
        <Button variant="secondary" disabled={busy !== null} onClick={() => run("png", "png")}>
          <PiImage /> PNG
        </Button>
        <Button
          variant="secondary"
          disabled={busy !== null || structuredDisabled}
          title={structuredDisabled ? "Log in to export structured data" : undefined}
          onClick={() => run("json", "json")}
        >
          <PiBracketsCurly /> JSON
        </Button>
        <Button
          variant="secondary"
          disabled={busy !== null || structuredDisabled}
          title={structuredDisabled ? "Log in to export an e-invoice" : undefined}
          onClick={() => run("ubl", "xml")}
        >
          <PiFileCode /> UBL
        </Button>
      </div>
      {structuredDisabled && (
        <p className="mt-2 text-xs text-gray-400">
          JSON & UBL (EN 16931 e-invoice) export requires an account — they identify
          you as the buyer.
        </p>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
