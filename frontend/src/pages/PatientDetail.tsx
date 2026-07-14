/** One patient, every kind of memory: chat, care plan, notes, tasks, timeline. */

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import type { Patient } from "../lib/types";
import Layout from "../components/Layout";
import AgentChat from "../components/AgentChat";
import CarePlanPanel from "../components/CarePlanPanel";
import NotesPanel from "../components/NotesPanel";
import TasksPanel from "../components/TasksPanel";
import TimelinePanel from "../components/TimelinePanel";
import { ErrorState, Spinner } from "../components/ui";

const TABS = ["Chat", "Care plan", "Notes & recall", "Tasks", "Timeline"] as const;
type Tab = (typeof TABS)[number];

export default function PatientDetail() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Chat");

  useEffect(() => {
    if (!patientId) return;
    api
      .getPatient(patientId)
      .then(setPatient)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Could not load patient."),
      );
  }, [patientId]);

  if (!patientId) return null;

  return (
    <Layout>
      <nav className="mb-4 text-sm text-ink-soft">
        <Link to="/patients" className="hover:text-ink">
          Patients
        </Link>{" "}
        / <span className="text-ink">{patient?.display_name ?? "…"}</span>
      </nav>

      {error && <ErrorState message={error} />}
      {!error && !patient && <Spinner label="Loading patient…" />}

      {patient && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-1">
            <h1 className="text-xl font-semibold text-ink">{patient.display_name}</h1>
            {patient.conditions.length > 0 && (
              <p className="text-sm text-ink-soft">{patient.conditions.join(" · ")}</p>
            )}
            {patient.allergies.length > 0 && (
              <p className="text-sm font-medium text-warn">
                Allergies: {patient.allergies.join(", ")}
              </p>
            )}
          </div>

          <div
            role="tablist"
            aria-label="Patient views"
            className="mb-5 flex flex-wrap gap-1 border-b border-line"
          >
            {TABS.map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={`-mb-px rounded-t-lg px-4 py-2 text-sm font-medium transition-colors ${
                  tab === t
                    ? "border-b-2 border-brand-500 text-brand-600"
                    : "text-ink-soft hover:text-ink"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="fade-up">
            {tab === "Chat" && <AgentChat patientId={patientId} />}
            {tab === "Care plan" && <CarePlanPanel patientId={patientId} />}
            {tab === "Notes & recall" && <NotesPanel patientId={patientId} />}
            {tab === "Tasks" && <TasksPanel patientId={patientId} />}
            {tab === "Timeline" && <TimelinePanel patientId={patientId} />}
          </div>
        </>
      )}
    </Layout>
  );
}
