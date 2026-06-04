// App shell: a top bar with the ZZPay logo + public nav, and the routed page
// below. There is no login wall — the account link simply reflects whether the
// visitor is currently recognised on this device.
import { Link, NavLink, Outlet } from "react-router-dom";
import {
  PiStorefront,
  PiGlobeSimple,
  PiReceipt,
  PiUserCircle,
  PiHouse,
} from "react-icons/pi";
import { useAuth } from "../auth";

const NAV = [
  { to: "/", label: "Home", icon: PiHouse, end: true },
  { to: "/merchant", label: "Merchant", icon: PiStorefront, end: false },
  { to: "/online-checkout", label: "Online", icon: PiGlobeSimple, end: false },
  { to: "/merchant/receipts", label: "Receipts", icon: PiReceipt, end: false },
];

export function Layout() {
  const { user } = useAuth();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${
      isActive ? "bg-brand/10 text-brand" : "text-gray-600 hover:text-gray-900"
    }`;

  return (
    <div className="min-h-full">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-2 px-4 py-3">
          <Link to="/" className="text-xl font-bold tracking-tight text-brand">
            ZZPay
          </Link>
          <nav className="flex items-center gap-1 overflow-x-auto">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass}>
                <Icon /> <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
            <NavLink to="/account" className={linkClass}>
              <PiUserCircle />{" "}
              <span className="hidden sm:inline">
                {user ? user.first_name : "Account"}
              </span>
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-4xl px-4 py-8 text-center text-xs text-gray-400">
        ZZPay MVP — Tap. Done. Booked. · structured receipt data at the source ·
        EN 16931-compatible
      </footer>
    </div>
  );
}
