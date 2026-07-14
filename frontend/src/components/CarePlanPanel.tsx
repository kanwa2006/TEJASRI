/** Care-plan editor: versioned, safety-gated, human-confirmed. */

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { CarePlanResponse, Medication } from "../lib/types";
import { Badge, Button, ErrorState, Input, SectionTitle, Spinner } from "./ui";
import SafetyReportView from "./SafetyReportView";

export default function CarePlanPanel({ patientId }: { patientId: string }) {
  const [data, setData] = useState<CarePlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Medication[]>([]);
  const [pendingWarning, setPendingWarning] = useState<CarePlanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [newMed, setNewMed] = useState({ name: "", dose: "", schedule: "" });

  const load = useCallback(async () => {
    setError(null);
    try {
      const plan = await api.getCarePlan(patientId);
      setData(plan);
      setDrafts(plan.plan.medications);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load care plan.");
    }
  }, [patientId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(acknowledge: boolean) {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.updateMedications(
        patientId,
        drafts,
        data.plan.version,
        acknowledge,
      );
      if (!result.applied) {
        setPendingWarning(result); // safety gate: human must confirm
      } else {
        setPendingWarning(null);
        setData(result);
        setDrafts(result.plan.medications);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed.");
      if (err instanceof ApiError && err.status === 409) await load();
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <ErrorState message={error} retry={load} />;
  if (!data) return <Spinner label="Loading care plan…" />;

  const dirty = JSON.stringify(drafts) !== JSON.stringify(data.plan.medications);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-line bg-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <SectionTitle sub={`Version ${data.plan.version} · every change is one transaction`}>
            Medications
          </SectionTitle>
          <Badge tone={data.plan.status === "active" ? "ok" : "review"}>
            {data.plan.status}
          </Badge>
        </div>

        <ul className="space-y-2">
          {drafts.map((med, index) => (
            <li
              key={index}
              className="flex items-center justify-between gap-2 rounded-lg bg-surface-2/60 px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium text-ink">{med.name}</span>{" "}
                <span className="text-ink-soft">
                  {med.dose} {med.schedule}
                </span>
              </div>
              <Button
                variant="ghost"
                aria-label={`Remove ${med.name}`}
                onClick={() => setDrafts(drafts.filter((_, i) => i !== index))}
              >
                ✕
              </Button>
            </li>
          ))}
          {drafts.length === 0 && (
            <li className="py-2 text-sm text-ink-soft">No active medications.</li>
          )}
        </ul>

        <form
          className="mt-3 grid grid-cols-[2fr_1fr_1fr_auto] gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newMed.name.trim()) return;
            setDrafts([...drafts, { ...newMed, name: newMed.name.trim(), rxnorm: null }]);
            setNewMed({ name: "", dose: "", schedule: "" });
          }}
        >
          <Input
            placeholder="Drug name"
            value={newMed.name}
            onChange={(e) => setNewMed({ ...newMed, name: e.target.value })}
            aria-label="Drug name"
          />
          <Input
            placeholder="Dose"
            value={newMed.dose}
            onChange={(e) => setNewMed({ ...newMed, dose: e.target.value })}
            aria-label="Dose"
          />
          <Input
            placeholder="Schedule"
            value={newMed.schedule}
            onChange={(e) => setNewMed({ ...newMed, schedule: e.target.value })}
            aria-label="Schedule"
          />
          <Button type="submit" variant="secondary">
            Add
          </Button>
        </form>

        {dirty && !pendingWarning && (
          <div className="mt-4 flex gap-2">
            <Button onClick={() => save(false)} disabled={busy}>
              {busy ? "Checking safety…" : "Save changes"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setDrafts(data.plan.medications)}
              disabled={busy}
            >
              Discard
            </Button>
          </div>
        )}

        {pendingWarning && (
          <div
            role="alertdialog"
            aria-label="Safety warnings require confirmation"
            className="fade-up mt-4 rounded-xl border border-warn/40 bg-warn/5 p-4"
          >
            <p className="mb-2 text-sm font-semibold text-warn">
              The safety engine flagged this change — it was NOT applied.
            </p>
            <SafetyReportView report={pendingWarning.safety} />
            <div className="mt-3 flex gap-2">
              <Button variant="danger" onClick={() => save(true)} disabled={busy}>
                I understand — apply anyway
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setPendingWarning(null);
                  setDrafts(data.plan.medications);
                }}
              >
                Cancel change
              </Button>
            </div>
          </div>
        )}
        {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      </div>

      <div className="rounded-xl border border-line bg-surface p-4">
        <SectionTitle sub={`Checked deterministically · dataset ${data.safety.dataset_version}`}>
          Current safety verdict
        </SectionTitle>
        <SafetyReportView report={data.safety} />
      </div>
    </div>
  );
}
