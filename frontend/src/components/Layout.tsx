import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api";

const navItems = [
  { to: "/", label: "Pulpit" },
  { to: "/datasets", label: "Zrzuty" },
  { to: "/events", label: "Oś czasu" },
  { to: "/mail", label: "Poczta" },
  { to: "/search", label: "Szukaj" },
  { to: "/people", label: "Osoby" },
  { to: "/graph", label: "Graf" },
  { to: "/entities", label: "Encje" },
  { to: "/topics", label: "Tematy" },
  { to: "/anomalies", label: "Anomalie" },
  { to: "/sources", label: "Źródła" },
];

export default function Layout() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const check = () =>
      api
        .health()
        .then(() => active && setHealthy(true))
        .catch(() => active && setHealthy(false));
    check();
    const id = setInterval(check, 10000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-4">
          <h1 className="text-lg font-semibold text-slate-800">Takeout Viewer</h1>
          <nav className="flex gap-1 ml-4">
            {navItems.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.to === "/"}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm ${
                    isActive
                      ? "bg-slate-900 text-white"
                      : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {it.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto text-xs flex items-center gap-2">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                healthy === null
                  ? "bg-slate-300"
                  : healthy
                    ? "bg-emerald-500"
                    : "bg-rose-500"
              }`}
            />
            <span className="text-slate-600">
              {healthy === null ? "Sprawdzanie..." : healthy ? "Backend działa" : "Brak połączenia"}
            </span>
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-4 pb-2 text-xs text-slate-500">
          Aplikacja działa lokalnie. Dane nie opuszczają tego komputera.
        </div>
      </header>
      <main className="flex-1">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <Outlet />
        </div>
      </main>
      <footer className="border-t border-slate-200 bg-white text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-4 py-2">
          Lokalna przeglądarka archiwów Google Takeout · v0.1
        </div>
      </footer>
    </div>
  );
}
