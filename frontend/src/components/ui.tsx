/** TEJASRI's small design system: consistent, accessible, calm. */

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  const styles = {
    primary:
      "bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 dark:text-canvas",
    secondary:
      "border border-line bg-surface text-ink hover:bg-surface-2 disabled:opacity-50",
    ghost: "text-ink-soft hover:text-ink hover:bg-surface-2 disabled:opacity-50",
    danger: "bg-danger text-white hover:opacity-90 disabled:opacity-50",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-soft/70 ${props.className ?? ""}`}
    />
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-line bg-surface p-5 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  sub,
}: {
  children: ReactNode;
  sub?: string;
}) {
  return (
    <div className="mb-3">
      <h2 className="text-base font-semibold text-ink">{children}</h2>
      {sub && <p className="mt-0.5 text-sm text-ink-soft">{sub}</p>}
    </div>
  );
}

const severityStyles: Record<string, string> = {
  minor: "bg-info/10 text-info",
  moderate: "bg-warn/10 text-warn",
  major: "bg-danger/10 text-danger",
  contraindicated: "bg-danger text-white",
  review: "bg-surface-2 text-ink-soft",
  ok: "bg-ok/10 text-ok",
};

export function Badge({
  tone = "review",
  children,
}: {
  tone?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${severityStyles[tone] ?? severityStyles.review}`}
    >
      {children}
    </span>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-ink-soft" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-brand-500" />
      {label}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="max-w-sm text-sm text-ink-soft">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-2 rounded-xl border border-danger/30 bg-danger/5 p-4"
    >
      <p className="text-sm font-medium text-danger">Something went wrong</p>
      <p className="text-sm text-ink-soft">{message}</p>
      {retry && (
        <Button variant="secondary" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}
