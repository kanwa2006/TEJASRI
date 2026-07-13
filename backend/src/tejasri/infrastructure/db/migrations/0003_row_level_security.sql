-- Row-Level Security: multi-tenant isolation enforced at the database.
--
-- Every session must run `SET app.tenant_id = '<uuid>'` before touching
-- these tables; the policies make rows of other tenants invisible even
-- through a shared connection, and FORCE applies the policy to table
-- owners too. current_setting(..., true) returns NULL when unset, which
-- makes the predicate false — no tenant context means no rows.

ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON patients
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);

ALTER TABLE care_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE care_plans FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON care_plans
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversations
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);

ALTER TABLE clinical_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_notes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON clinical_notes
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tasks
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_log
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::UUID);
