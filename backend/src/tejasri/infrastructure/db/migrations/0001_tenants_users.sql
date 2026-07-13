-- Tenants (clinics/orgs) and the authentication directory.
--
-- `users` deliberately has NO row-level security: it is an auth directory,
-- not patient data. Login must resolve a user by email before a tenant
-- context exists. Every PHI-shaped table (see 0002/0003) is RLS-forced.

CREATE TABLE IF NOT EXISTS tenants (
  tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name STRING NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  email STRING NOT NULL UNIQUE,
  password_hash STRING NOT NULL,
  role STRING NOT NULL DEFAULT 'coordinator',
  display_name STRING NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT users_role_check CHECK (role IN ('patient', 'caregiver', 'coordinator', 'admin')),
  INDEX idx_users_tenant (tenant_id)
);
