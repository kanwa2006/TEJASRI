/** Minimal typed API client. Token lives in localStorage; a 401 clears it. */

import type {
  AgentTurnResponse,
  AuditEntry,
  AuthResponse,
  CarePlanResponse,
  CarePlanUpdateResponse,
  ConversationMessage,
  Medication,
  Note,
  Patient,
  RecalledNote,
  TaskItem,
  TimelineEvent,
} from "./types";

const TOKEN_KEY = "tejasri.token";
const ROLE_KEY = "tejasri.role";

export const session = {
  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  get role(): string | null {
    return localStorage.getItem(ROLE_KEY);
  },
  save(auth: AuthResponse) {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem(ROLE_KEY, auth.role);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  },
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  const token = session.token;
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`/api/v1${path}`, { ...init, headers });
  if (response.status === 401) {
    session.clear();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  register: (body: {
    tenant_name: string;
    admin_email: string;
    admin_password: string;
    admin_display_name: string;
  }) => request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(body) }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listPatients: () => request<Patient[]>("/patients"),
  getPatient: (id: string) => request<Patient>(`/patients/${id}`),
  createPatient: (body: {
    display_name: string;
    dob?: string | null;
    conditions: string[];
    allergies: string[];
  }) => request<Patient>("/patients", { method: "POST", body: JSON.stringify(body) }),

  getCarePlan: (patientId: string) => request<CarePlanResponse>(`/patients/${patientId}/care-plan`),
  updateMedications: (
    patientId: string,
    medications: Medication[],
    expectedVersion: number,
    acknowledgeWarnings: boolean,
  ) =>
    request<CarePlanUpdateResponse>(`/patients/${patientId}/care-plan/medications`, {
      method: "PUT",
      body: JSON.stringify({
        medications,
        expected_version: expectedVersion,
        acknowledge_warnings: acknowledgeWarnings,
      }),
    }),

  agentTurn: (patientId: string, message: string) =>
    request<AgentTurnResponse>(`/patients/${patientId}/agent/turn`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  conversation: (patientId: string) =>
    request<ConversationMessage[]>(`/patients/${patientId}/conversation`),

  listNotes: (patientId: string) => request<Note[]>(`/patients/${patientId}/notes`),
  createNote: (patientId: string, noteText: string) =>
    request<Note>(`/patients/${patientId}/notes`, {
      method: "POST",
      body: JSON.stringify({ note_text: noteText }),
    }),
  recallNotes: (patientId: string, q: string) =>
    request<RecalledNote[]>(
      `/patients/${patientId}/notes/recall?q=${encodeURIComponent(q)}&limit=5`,
    ),

  listTasks: (patientId: string) => request<TaskItem[]>(`/patients/${patientId}/tasks`),
  createTask: (patientId: string, kind: TaskItem["kind"]) =>
    request<TaskItem>(`/patients/${patientId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ kind, payload: {} }),
    }),
  transitionTask: (taskId: string, toState: TaskItem["state"]) =>
    request<TaskItem>(`/tasks/${taskId}/transition`, {
      method: "POST",
      body: JSON.stringify({ to_state: toState }),
    }),

  timeline: (patientId: string) => request<TimelineEvent[]>(`/patients/${patientId}/timeline`),
  audit: (patientId?: string) =>
    request<AuditEntry[]>(`/audit${patientId ? `?patient_id=${patientId}` : ""}`),
};
