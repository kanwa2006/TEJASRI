# Roadmap

TEJASRI is a Healthcare Memory Platform. Version 1 is one vertical slice built to production quality; everything else is a documented extension, not a half-feature.

## Version 1 (in progress) — Medication Adherence & Care Continuity

Delivered in phases (see BLUEPRINT.md, "Implementation Phases"):

1. **Foundation** — repository, architecture, conventions, dev environment ✅
2. **Core backend** — database schema + migrations, RLS, authentication, API foundation
3. **Agent memory** — vector-indexed semantic recall (C-SPANN), conversation memory, MCP integration, AWS Lambda/S3
4. **Healthcare workflows** — agent orchestrator, deterministic safety engine, explainability, task state machine
5. **Frontend** — patient/coordinator experience, timelines, evidence viewer
6. **Hardening** — testing depth, security review, performance, observability, resilience demo
7. **Polish** — documentation completeness, deployment, demo

## Extension modules (designed-for, not built in v1)

These attach through existing extension points (new use cases, adapters, routers) without redesign:

- **Hospital Memory** — cross-encounter institutional memory
- **Clinical Timeline** — longitudinal event visualization
- **Caregiver Portal** — family/caregiver views with scoped access
- **Emergency Summary** — one-page critical-context handoff
- **Doctor Workspace** — clinician-facing review and override tooling
- **FHIR Adapter** — interoperability with real EHR systems (the compliance boundary for real data)
- **Bedrock Adapter** — AWS-native LLM provider (adapter exists, dormant)
- **Hospital Integration Layer & Plugin Architecture** — third-party module surface
- **Longitudinal Patient Intelligence** — trend analysis over durable memory

## Principles that govern the roadmap

- Roadmap features never delay Version 1.
- Anything that would weaken the safety model (deterministic-authoritative, human-in-the-loop) is out of scope permanently.
- Real patient data only ever enters through a compliant FHIR adapter — never before.
