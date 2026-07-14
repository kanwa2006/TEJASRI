/** Sign in / create a clinic. The first thing a user reads is the mission. */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, session } from "../lib/api";
import { Button, Card, Input } from "../components/ui";
import { DisclaimerBanner, ThemeToggle } from "../components/Layout";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const auth =
        mode === "login"
          ? await api.login(email, password)
          : await api.register({
              tenant_name: tenantName,
              admin_email: email,
              admin_password: password,
              admin_display_name: displayName,
            });
      session.save(auth);
      navigate("/patients");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <DisclaimerBanner />
      <div className="absolute right-4 top-10">
        <ThemeToggle />
      </div>
      <div className="mx-auto grid min-h-[85vh] max-w-5xl items-center gap-10 px-4 md:grid-cols-2">
        <section className="fade-up">
          <h1 className="text-3xl font-bold tracking-tight text-brand-600">TEJASRI</h1>
          <p className="mt-3 text-xl font-semibold text-ink">
            Healthcare should never forget.
          </p>
          <p className="mt-3 max-w-md text-sm leading-6 text-ink-soft">
            TEJASRI is a healthcare memory platform. Care plans, conversations, and
            clinical context live in a durable, transactional memory that survives
            failures with zero loss — while humans stay in control of every decision.
          </p>
          <ul className="mt-5 space-y-2 text-sm text-ink-soft">
            <li>• Memory before intelligence — every fact is durable and recallable</li>
            <li>• Deterministic drug-safety checks; the AI only explains</li>
            <li>• Every recommendation shows its evidence and sources</li>
            <li>• Tenant isolation enforced by the database itself</li>
          </ul>
        </section>

        <Card className="fade-up">
          <div className="mb-4 flex rounded-lg bg-surface-2 p-1" role="tablist">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                role="tab"
                aria-selected={mode === m}
                onClick={() => setMode(m)}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  mode === m ? "bg-surface text-ink shadow-sm" : "text-ink-soft"
                }`}
              >
                {m === "login" ? "Sign in" : "Create a clinic"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <>
                <label className="block text-sm">
                  <span className="mb-1 block text-ink-soft">Clinic / organization name</span>
                  <Input
                    required
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    placeholder="Sunrise Clinic"
                  />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block text-ink-soft">Your name</span>
                  <Input
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Dr. Asha Rao"
                  />
                </label>
              </>
            )}
            <label className="block text-sm">
              <span className="mb-1 block text-ink-soft">Email</span>
              <Input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@clinic.example"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-ink-soft">
                Password {mode === "register" && "(12+ characters)"}
              </span>
              <Input
                required
                type="password"
                minLength={mode === "register" ? 12 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create clinic"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
