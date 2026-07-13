# ADR 0003 — Provider-agnostic LLM adapter (Gemini default, Ollama fallback, Bedrock dormant)

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

The platform needs text generation (explanations) and embeddings (semantic memory) at ~$0 cost, with zero provider lock-in and a credible path to AWS Bedrock. Gemini's free tier may use inputs for model training — acceptable only because all data is synthetic.

## Decision

- A single `LLMProvider` interface in the domain layer: `generate(...)` and `embed(...)`.
- Adapters: **Gemini** (default, free Flash tier), **Ollama** (local, automatic failover target on 429/5xx), **Bedrock** (implemented as an adapter but dormant — no meaningful free tier).
- Provider selected via `LLM_PROVIDER` env var; failover order configurable.
- **Embeddings default to local sentence-transformers** (`bge-small-en-v1.5`, 384-dim → `VECTOR(384)`): deterministic, offline, $0, and no data leaves the machine.

## Rationale

- Ports-and-adapters keeps the agent orchestrator independent of any vendor SDK.
- Local embeddings decouple the load-bearing memory (vectors) from third-party availability and privacy policies.
- Bedrock swap-in demonstrates AWS alignment without incurring cost.

## Consequences

- Embedding dimension (384) is fixed in the schema; changing embedding models requires a migration and re-embedding job (handled by the nightly Lambda).
- Failover must be covered by tests (simulated 429/5xx).
- Never send non-synthetic data to hosted LLM APIs.
