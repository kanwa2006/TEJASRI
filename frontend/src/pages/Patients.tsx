/** Patient roster: the coordinator's home. */

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import type { Patient } from "../lib/types";
import Layout from "../components/Layout";
import { Button, Card, EmptyState, ErrorState, Input, SectionTitle, Spinner } from "../components/ui";

export default function Patients() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [conditions, setConditions] = useState("");
  const [allergies, setAllergies] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setPatients(await api.listPatients());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createPatient(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.createPatient({
        display_name: name,
        conditions: conditions.split(",").map((s) => s.trim()).filter(Boolean),
        allergies: allergies.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setName("");
      setConditions("");
      setAllergies("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create patient.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Patients</h1>
          <p className="text-sm text-ink-soft">
            Longitudinal memory for every person in your care.
          </p>
        </div>
        <Button onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Close" : "Add patient"}
        </Button>
      </div>

      {showForm && (
        <Card className="fade-up mb-5">
          <SectionTitle sub="Synthetic data only — never enter real patient information.">
            New patient
          </SectionTitle>
          <form onSubmit={createPatient} className="grid gap-3 sm:grid-cols-3">
            <Input
              required
              placeholder="Full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              placeholder="Conditions (comma-separated)"
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
            />
            <Input
              placeholder="Allergies (comma-separated)"
              value={allergies}
              onChange={(e) => setAllergies(e.target.value)}
            />
            <Button type="submit" disabled={busy} className="sm:col-span-3 sm:w-fit">
              {busy ? "Creating…" : "Create patient"}
            </Button>
          </form>
        </Card>
      )}

      {error && <ErrorState message={error} retry={load} />}
      {!error && patients === null && <Spinner label="Loading patients…" />}
      {!error && patients?.length === 0 && (
        <EmptyState
          title="No patients yet"
          hint="Add your first (synthetic) patient to see TEJASRI's memory in action."
          action={<Button onClick={() => setShowForm(true)}>Add patient</Button>}
        />
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {patients?.map((patient) => (
          <Link key={patient.patient_id} to={`/patients/${patient.patient_id}`}>
            <Card className="fade-up h-full transition-shadow hover:shadow-md">
              <p className="font-semibold text-ink">{patient.display_name}</p>
              <p className="mt-1 text-sm text-ink-soft">
                {patient.conditions.length
                  ? patient.conditions.join(", ")
                  : "No recorded conditions"}
              </p>
              {patient.allergies.length > 0 && (
                <p className="mt-2 text-xs font-medium text-warn">
                  Allergies: {patient.allergies.join(", ")}
                </p>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </Layout>
  );
}
