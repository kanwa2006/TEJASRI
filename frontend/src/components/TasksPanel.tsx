/** Workflow tasks: a visible, validated state machine. */

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { TaskItem } from "../lib/types";
import { Badge, Button, EmptyState, ErrorState, Spinner } from "./ui";

const NEXT_STATES: Record<TaskItem["state"], TaskItem["state"][]> = {
  open: ["in_progress", "blocked", "done"],
  in_progress: ["blocked", "done"],
  blocked: ["open", "in_progress"],
  done: [],
};

const stateTone: Record<TaskItem["state"], string> = {
  open: "review",
  in_progress: "minor",
  blocked: "moderate",
  done: "ok",
};

export default function TasksPanel({ patientId }: { patientId: string }) {
  const [tasks, setTasks] = useState<TaskItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setTasks(await api.listTasks(patientId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load tasks.");
    }
  }, [patientId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function transition(taskId: string, to: TaskItem["state"]) {
    try {
      await api.transitionTask(taskId, to);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Transition failed.");
    }
  }

  async function create(kind: TaskItem["kind"]) {
    try {
      await api.createTask(patientId, kind);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create task.");
    }
  }

  if (error && !tasks) return <ErrorState message={error} retry={load} />;
  if (tasks === null) return <Spinner label="Loading tasks…" />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {(["refill", "pharmacist_review", "followup", "adherence_check"] as const).map(
          (kind) => (
            <Button key={kind} variant="secondary" onClick={() => create(kind)}>
              + {kind.replace("_", " ")}
            </Button>
          ),
        )}
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}

      {tasks.length === 0 ? (
        <EmptyState
          title="No tasks"
          hint="Tasks are the agent's durable to-do state — they survive restarts and are created nightly by the adherence Lambda."
        />
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => (
            <li
              key={task.task_id}
              className="fade-up flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-surface px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <Badge tone={stateTone[task.state]}>{task.state.replace("_", " ")}</Badge>
                <span className="text-sm font-medium text-ink">
                  {task.kind.replace("_", " ")}
                </span>
                <time className="text-xs text-ink-soft">
                  {new Date(task.updated_at).toLocaleString()}
                </time>
              </div>
              <div className="flex gap-1.5">
                {NEXT_STATES[task.state].map((to) => (
                  <Button
                    key={to}
                    variant="ghost"
                    onClick={() => transition(task.task_id, to)}
                  >
                    → {to.replace("_", " ")}
                  </Button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
