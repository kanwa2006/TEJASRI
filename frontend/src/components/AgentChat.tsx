/** The agent conversation with a full explainability panel.
    Every answer shows: evidence recalled from memory, the deterministic
    safety verdict, which provider answered, and retrieval confidence. */

import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import type { AgentTurnResponse, ConversationMessage } from "../lib/types";
import { Badge, Button, EmptyState, Input, Spinner } from "./ui";
import SafetyReportView from "./SafetyReportView";

export default function AgentChat({ patientId }: { patientId: string }) {
  const [history, setHistory] = useState<ConversationMessage[] | null>(null);
  const [lastTurn, setLastTurn] = useState<AgentTurnResponse | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .conversation(patientId)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [patientId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [history, busy]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    const text = message.trim();
    setMessage("");
    setError(null);
    setBusy(true);
    setHistory((h) => [
      ...(h ?? []),
      {
        message_id: `local-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const turn = await api.agentTurn(patientId, text);
      setLastTurn(turn);
      setHistory((h) => [
        ...(h ?? []),
        {
          message_id: `local-a-${Date.now()}`,
          role: "agent",
          content: turn.answer,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The agent could not respond.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="flex h-[520px] flex-col rounded-xl border border-line bg-surface">
        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
          {history === null && <Spinner label="Loading conversation…" />}
          {history?.length === 0 && !busy && (
            <EmptyState
              title="Start the conversation"
              hint='Try: "What medications am I taking?" or "Can I take ibuprofen with my current meds?"'
            />
          )}
          {history?.map((m) => (
            <div
              key={m.message_id}
              className={`fade-up max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-6 ${
                m.role === "user"
                  ? "ml-auto bg-brand-600 text-white dark:text-canvas"
                  : "bg-surface-2 text-ink"
              }`}
            >
              {m.content}
            </div>
          ))}
          {busy && <Spinner label="Recalling memory, checking safety…" />}
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
        </div>
        <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about medications, history, or safety…"
            aria-label="Message the agent"
            disabled={busy}
          />
          <Button type="submit" disabled={busy || !message.trim()}>
            Send
          </Button>
        </form>
      </div>

      <aside className="space-y-4">
        <div className="rounded-xl border border-line bg-surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-ink">Why this answer</h3>
          {!lastTurn ? (
            <p className="text-sm text-ink-soft">
              After each reply, the full evidence chain appears here — recalled
              history, the deterministic safety verdict, and provenance. TEJASRI
              never answers from a black box.
            </p>
          ) : (
            <div className="space-y-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={lastTurn.degraded ? "moderate" : "ok"}>
                  {lastTurn.provider}
                </Badge>
                {lastTurn.disclosure_enforced && (
                  <Badge tone="major">disclosure enforced</Badge>
                )}
                <span className="text-xs text-ink-soft">
                  plan v{lastTurn.care_plan_version}
                </span>
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  Retrieval confidence
                </p>
                <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className="h-full rounded-full bg-brand-500 transition-all"
                    style={{ width: `${Math.round(lastTurn.retrieval_confidence * 100)}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  {Math.round(lastTurn.retrieval_confidence * 100)}% — from vector
                  distance of recalled memory
                </p>
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  Evidence · recalled from memory
                </p>
                {lastTurn.evidence.length === 0 ? (
                  <p className="text-xs text-ink-soft">No relevant history found.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {lastTurn.evidence.map((e) => (
                      <li
                        key={e.note_id}
                        className="rounded-lg bg-surface-2/60 p-2 text-xs leading-5 text-ink-soft"
                      >
                        {e.note_text}
                        <span className="mt-0.5 block text-[10px] text-ink-soft/70">
                          L2 distance {e.distance.toFixed(3)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  Safety verdict · deterministic
                </p>
                <SafetyReportView report={lastTurn.safety} />
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
