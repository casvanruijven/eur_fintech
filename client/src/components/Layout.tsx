// App shell for authenticated pages: a top bar with the ZZPay logo, nav, and
// logout, plus the routed page content below.
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { PiReceipt, PiSignOut, PiUserCircle } from "react-icons/pi";
import { useAuth } from "../auth";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${
      isActive ? "bg-brand/10 text-brand" : "text-gray-600 hover:text-gray-900"
    }`;

  return (
    <div className="min-h-full">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-xl font-bold tracking-tight text-brand">
            ZZPay
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={linkClass}>
              <PiReceipt /> Bonnen
            </NavLink>
            <NavLink to="/account" className={linkClass}>
              <PiUserCircle /> Account
            </NavLink>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              <PiSignOut /> Uitloggen
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6">
        <p className="mb-4 text-sm text-gray-500">
          Ingelogd als {user?.first_name} {user?.last_name}
        </p>
        <Outlet />
      </main>
    </div>
  );
}
