/** App shell: header, permanent disclaimer, theme toggle, sign-out. */

import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { session } from "../lib/api";
import { Button } from "./ui";

const THEME_KEY = "tejasri.theme";

export function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem(THEME_KEY) === "dark");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

export function ThemeToggle() {
  const { dark, toggle } = useTheme();
  return (
    <Button
      variant="ghost"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
    >
      {dark ? "☀" : "☾"}
    </Button>
  );
}

export function DisclaimerBanner() {
  return (
    <p className="border-b border-line bg-surface-2 px-4 py-1.5 text-center text-xs text-ink-soft">
      TEJASRI is an assistive tool, not a medical device. It never replaces clinical
      judgment. All data shown is synthetic.
    </p>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const role = session.role;

  return (
    <div className="min-h-screen">
      <DisclaimerBanner />
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/patients" className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight text-brand-600">
              TEJASRI
            </span>
            <span className="hidden text-xs text-ink-soft sm:inline">
              healthcare should never forget
            </span>
          </Link>
          <div className="flex items-center gap-1.5">
            {role && (
              <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-600">
                {role}
              </span>
            )}
            <ThemeToggle />
            <Button
              variant="ghost"
              onClick={() => {
                session.clear();
                navigate("/login");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
