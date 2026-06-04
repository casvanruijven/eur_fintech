// All routes are public — the whole point of ZZPay is "no app, no login" receipt
// access. The optional account only unlocks structured export + emailing, handled
// inside the receipt actions, not by gating whole pages.
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Landing } from "./pages/Landing";
import { MerchantCheckout } from "./pages/MerchantCheckout";
import { MerchantReceipts } from "./pages/MerchantReceipts";
import { OnlineCheckout } from "./pages/OnlineCheckout";
import { ReceiptView } from "./pages/ReceiptView";
import { Account } from "./pages/Account";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/merchant" element={<MerchantCheckout />} />
        <Route path="/merchant/receipts" element={<MerchantReceipts />} />
        <Route path="/online-checkout" element={<OnlineCheckout />} />
        <Route path="/receipt/:id" element={<ReceiptView />} />
        <Route path="/account" element={<Account />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
