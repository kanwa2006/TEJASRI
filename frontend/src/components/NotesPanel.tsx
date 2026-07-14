/** Clinical notes + live semantic recall — memory you can watch working. */

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import type { Note, RecalledNote } from "../lib/types";
import { Button, EmptyState, ErrorState, Input, SectionTitle, Spinner } from "./ui";

export default function NotesPanel({ patientId }: { patientId: string }) {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecalledNote[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setNotes(await api.listNotes(patientId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load notes.");
    }
  }, [patientId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    setBusy(true);
    try {
      await api.createNote(patientId, draft.trim());
      setDraft("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save note.");
    } finally {
      setBusy(false);
    }
  }

  async function recall(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    try {
      setResults(await api.recallNotes(patientId, query.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Recall failed.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !notes) return <ErrorState message={error} retry={load} />;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-line bg-surface p-4">
        <SectionTitle sub="Each note is embedded and stored in the vector-indexed memory the moment its transaction commits.">
          Clinical notes
        </SectionTitle>
        <form onSubmit={addNote} className="mb-3 flex gap-2">
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. Started metformin 500mg twice daily for type 2 diabetes"
            aria-label="New clinical note"
          />
          <Button type="submit" disabled={busy || !draft.trim()}>
            Add
          </Button>
        </form>
        {notes === null && <Spinner label="Loading notes…" />}
        {notes?.length === 0 && (
          <EmptyState title="No notes yet" hint="Add a note to give the agent memory to recall." />
        )}
        <ul className="space-y-2">
          {notes?.map((note) => (
            <li
              key={note.note_id}
              className="rounded-lg bg-surface-2/60 p-3 text-sm leading-6 text-ink"
            >
              {note.note_text}
              <time className="mt-1 block text-xs text-ink-soft">
                {new Date(note.created_at).toLocaleString()}
              </time>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <SectionTitle sub="Query the C-SPANN vector index directly — lower L2 distance means closer meaning.">
          Semantic recall
        </SectionTitle>
        <form onSubmit={recall} className="mb-3 flex gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "diabetes medication"'
            aria-label="Recall query"
          />
          <Button type="submit" variant="secondary" disabled={busy || !query.trim()}>
            Recall
          </Button>
        </form>
        {results === null ? (
          <p className="text-sm text-ink-soft">
            Results appear ranked by semantic similarity, with their distances shown —
            the same recall the agent uses to ground its answers.
          </p>
        ) : results.length === 0 ? (
          <EmptyState title="Nothing recalled" hint="Add notes first, then search by meaning." />
        ) : (
          <ol className="space-y-2">
            {results.map((r, i) => (
              <li
                key={r.note.note_id}
                className="fade-up rounded-lg border border-line p-3 text-sm leading-6"
              >
                <span className="mr-2 font-semibold text-brand-600">#{i + 1}</span>
                {r.note.note_text}
                <span className="mt-1 block text-xs text-ink-soft">
                  L2 distance {r.distance.toFixed(3)}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
