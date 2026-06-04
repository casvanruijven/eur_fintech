// Landing page — the investor-facing pitch in one screen.
import { Link } from "react-router-dom";
import { PiStorefront, PiGlobeSimple, PiArrowRight } from "react-icons/pi";
import { Card } from "../components/Card";

export function Landing() {
  return (
    <div className="space-y-10">
      <section className="pt-6 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl">
          Tap. Done. <span className="text-brand">Booked.</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-gray-600">
          No app. No scanning. No OCR. ZZPay turns a checkout into clean, structured,
          tax-ready receipt data <strong>at the source</strong> — delivered to the buyer
          in a plain browser.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            to="/merchant"
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-5 py-3 font-medium text-white hover:bg-brand-dark"
          >
            <PiStorefront /> Merchant demo (NFC)
          </Link>
          <Link
            to="/online-checkout"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-5 py-3 font-medium text-gray-800 hover:bg-gray-50"
          >
            <PiGlobeSimple /> Online checkout demo
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Feature title="Structured at the source">
          Captured directly from the point-of-sale — never a photo of a faded receipt.
        </Feature>
        <Feature title="One infrastructure, many channels">
          NFC tap or online link deliver the <em>same</em> structured receipt. QR, email
          and POS APIs are just more channels.
        </Feature>
        <Feature title="EN 16931 e-invoice ready">
          Export a compliant UBL e-invoice that imports straight into bookkeeping
          software. Refunds become auditable credit notes.
        </Feature>
      </section>

      <section>
        <Card className="bg-brand/5 p-6">
          <p className="text-sm leading-relaxed text-gray-700">
            <strong>For investors:</strong> ZZPay reduces the admin burden of the
            self-employed by capturing receipt data at the source. This MVP proves a
            merchant can create an EN 16931-compatible digital receipt with one click,
            deliver it over NFC or an online link, and let the user export, email, or
            refund it — without installing an app or creating an account. It validates the
            core infrastructure layer <em>before</em> expensive POS integrations and
            large-scale merchant rollout.
          </p>
        </Card>
      </section>

      <section className="flex flex-wrap justify-center gap-4 text-sm">
        <Link to="/merchant" className="inline-flex items-center gap-1 text-brand hover:underline">
          Start the merchant flow <PiArrowRight />
        </Link>
      </section>
    </div>
  );
}

function Feature({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <h3 className="font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-600">{children}</p>
    </Card>
  );
}
