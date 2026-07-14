/** Chronological view over every kind of memory — the continuity story. */

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { TimelineEvent } from "../lib/types";
import { EmptyState, ErrorState, Spinner } from "./ui";

const kindStyles: Record<TimelineEvent["kind"], { dot: string; label: string }> = {
  conversation: { dot: "bg-info", label: "Conversation" },
  note: { dot: "bg-brand-500", label: "Clinical note" },
  task: { dot: "bg-warn", label: "Task" },
  audit: { dot: "bg-ink-soft", label: "Audit" },
};

export default function TimelinePanel({ patientId }: { patientId: string }) {
  const [events, setEvents] = useState<TimelineEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setEvents(await api.timeline(patientId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load timeline.");
    }
  }, [patientId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorState message={error} retry={load} />;
  if (events === null) return <Spinner label="Loading timeline…" />;
  if (events.length === 0)
    return (
      <EmptyState
        title="Nothing recorded yet"
        hint="Conversations, notes, tasks, and audited actions will appear here in one continuous history."
      />
    );

  return (
    <ol className="relative ml-3 space-y-4 border-l border-line pl-5">
      {events.map((event, i) => {
        const style = kindStyles[event.kind];
        return (
          <li key={i} className="fade-up relative">
            <span
              className={`absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full ${style.dot}`}
              aria-hidden
            />
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
                {style.label}
              </span>
              <time className="text-xs text-ink-soft/80" dateTime={event.at}>
                {new Date(event.at).toLocaleString()}
              </time>
            </div>
            <p className="mt-0.5 text-sm font-medium text-ink">{event.title}</p>
            {event.detail && (
              <p className="mt-0.5 max-w-2xl text-sm leading-6 text-ink-soft">
                {event.detail.length > 240
                  ? `${event.detail.slice(0, 240)}…`
                  : event.detail}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
