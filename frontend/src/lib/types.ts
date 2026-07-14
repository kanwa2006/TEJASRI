/** API contract types — mirror backend Pydantic response models. */

export interface AuthResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user_id: string;
  role: string;
}

export interface Patient {
  patient_id: string;
  display_name: string;
  external_ref: string | null;
  dob: string | null;
  conditions: string[];
  allergies: string[];
}

export interface Medication {
  name: string;
  dose: string;
  schedule: string;
  rxnorm: string | null;
}

export interface SafetyFlag {
  kind: "interaction" | "allergy" | "unknown_drug";
  drugs: string[];
  severity: "minor" | "moderate" | "major" | "contraindicated" | null;
  description: string;
  source: string;
  needs_confirmation: boolean;
}

export interface SafetyReport {
  flags: SafetyFlag[];
  checked_pairs: number;
  dataset_version: string;
  unknown_drugs: string[];
  max_severity: string | null;
}

export interface CarePlan {
  care_plan_id: string;
  status: string;
  medications: Medication[];
  version: number;
  updated_at: string;
}

export interface CarePlanResponse {
  plan: CarePlan;
  safety: SafetyReport;
}

export interface CarePlanUpdateResponse extends CarePlanResponse {
  applied: boolean;
}

export interface Evidence {
  note_id: string;
  note_text: string;
  distance: number;
}

export interface AgentTurnResponse {
  answer: string;
  safety: SafetyReport;
  evidence: Evidence[];
  care_plan_version: number;
  provider: string;
  degraded: boolean;
  retrieval_confidence: number;
  disclosure_enforced: boolean;
}

export interface ConversationMessage {
  message_id: string;
  role: "user" | "agent" | "system";
  content: string;
  created_at: string;
}

export interface Note {
  note_id: string;
  note_text: string;
  created_at: string;
}

export interface RecalledNote {
  note: Note;
  distance: number;
}

export interface TaskItem {
  task_id: string;
  patient_id: string;
  kind: "refill" | "pharmacist_review" | "followup" | "adherence_check";
  state: "open" | "in_progress" | "blocked" | "done";
  payload: Record<string, unknown>;
  updated_at: string;
}

export interface TimelineEvent {
  kind: "conversation" | "note" | "task" | "audit";
  at: string;
  title: string;
  detail: string;
}

export interface AuditEntry {
  audit_id: string;
  patient_id: string | null;
  actor: string;
  action: string;
  detail: Record<string, unknown>;
  created_at: string;
}
