# ADR 0004 — Deterministic safety engine; LLM explains only

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

Drug–drug interaction and allergy checking cannot depend on a probabilistic model: hallucinated or omitted severities are unacceptable. The NLM RxNav drug–drug interaction API was discontinued (Jan 2024), so interaction data must come from local deterministic datasets.

## Decision

- Interaction/allergy checks run against **deterministic datasets**: DDInter 2.0 (primary), openFDA drug labels (fallback), with **RxNorm** for drug-name → RxCUI normalization.
- The safety engine's verdict (flags + severities + sources) is **authoritative**. The LLM receives it as context and may only explain it. Post-processing enforces that:
  - every flag raised by the engine is disclosed in the response;
  - severity ratings in the response match the engine's output verbatim.
- Low-confidence name normalization → `needs_confirmation = true`, surfaced to a human.
- Safety-check results are persisted to `audit_log` on every agent turn.

## Rationale

This is the core trust property of the platform ("Safety before automation", "Doctors before AI"). It is also a genuine differentiator versus LLM-only health chatbots.

## Consequences

- Safety datasets ship as versioned local artifacts (stored in S3, loaded at startup); dataset updates are explicit, reviewed changes.
- The engine must be pure/deterministic → property-style unit tests, no network in the hot path.
- TEJASRI remains assistive, not a medical device; disclaimers are mandatory in every surface.
