-- The TEJASRI memory core (docs/BLUEPRINT.md, Part D).
--
-- Four kinds of load-bearing agent memory, all in one system of record:
--   transactional  : care_plans (versioned), tasks (state machine)
--   short-term     : conversations
--   long-term      : clinical_notes with VECTOR(384) + C-SPANN index
--   accountability : audit_log
--
-- Prerequisite (applied by ops/bootstrap, cannot run inside a migration):
--   SET CLUSTER SETTING feature.vector_index.enabled = true;

CREATE TABLE IF NOT EXISTS patients (
  patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  external_ref STRING,
  display_name STRING NOT NULL,
  dob DATE,
  conditions STRING[] NOT NULL DEFAULT ARRAY[],
  allergies STRING[] NOT NULL DEFAULT ARRAY[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  INDEX idx_patients_tenant (tenant_id)
);

CREATE TABLE IF NOT EXISTS care_plans (
  care_plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),
  status STRING NOT NULL DEFAULT 'active',
  medications JSONB NOT NULL DEFAULT '[]',
  version INT NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT care_plans_status_check CHECK (status IN ('active', 'paused', 'closed')),
  INDEX idx_care_plans_patient (tenant_id, patient_id)
);

CREATE TABLE IF NOT EXISTS conversations (
  message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),
  role STRING NOT NULL,
  content STRING NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT conversations_role_check CHECK (role IN ('user', 'agent', 'system')),
  INDEX idx_conv_patient_time (tenant_id, patient_id, created_at DESC)
);

CREATE TABLE IF NOT EXISTS clinical_notes (
  note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),
  note_text STRING NOT NULL,
  embedding VECTOR(384) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  VECTOR INDEX idx_notes_vec (tenant_id, patient_id, embedding)
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),
  kind STRING NOT NULL,
  state STRING NOT NULL DEFAULT 'open',
  payload JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT tasks_kind_check CHECK (kind IN ('refill', 'pharmacist_review', 'followup', 'adherence_check')),
  CONSTRAINT tasks_state_check CHECK (state IN ('open', 'in_progress', 'blocked', 'done')),
  INDEX idx_tasks_patient (tenant_id, patient_id, state)
);

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  patient_id UUID,
  actor STRING NOT NULL,
  action STRING NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  INDEX idx_audit_tenant_time (tenant_id, created_at DESC)
);
