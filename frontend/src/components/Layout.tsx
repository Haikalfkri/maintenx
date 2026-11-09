import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { ROLE_LABELS } from "../constants";
import { useAuth } from "../hooks/auth-context";
import { fullName } from "../utils";
import { buttonSecondary } from "./styles";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/equipment", label: "Equipment", end: false },
];

function navClass({ isActive }: { isActive: boolean }) {
  return `block rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100"
  }`;
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
        <p className="mb-6 px-3 text-lg font-bold text-blue-700">MaintenX</p>
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{user?.organization.name}</p>
            <p className="truncate text-xs text-slate-500">
              {user && fullName(user)} · {user && ROLE_LABELS[user.role]}
            </p>
          </div>
          <button type="button" onClick={handleLogout} className={buttonSecondary}>
            Log out
          </button>
        </header>

        {/* Navigasi untuk layar kecil */}
        <nav className="flex gap-2 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}