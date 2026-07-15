# TEJASRI Frontend

The patient/coordinator web experience for the TEJASRI Healthcare Memory
Platform — React + TypeScript + Vite, styled with Tailwind v4. See the
[project README](../README.md) for the product and architecture.

## What's here

- Agent chat with a full explainability panel (recalled evidence with vector
  distances, the deterministic safety verdict with sources, provider and
  degradation badges, retrieval confidence)
- Care-plan editor with the human-confirmation safety gate
- Semantic-recall explorer, task board, and unified timeline
- Dark/light themes, keyboard-visible focus, and real loading / empty / error states

## Develop

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to http://127.0.0.1:8000
npm run lint     # oxlint
npm run build    # type-check (tsc -b) + production build
```

The dev server proxies `/api` to the backend (see [vite.config.ts](vite.config.ts)),
so run the backend on port 8000 alongside it (`uvicorn tejasri.main:app`).

## Layout

```
src/
  components/   UI primitives (ui.tsx) and feature panels (AgentChat, CarePlanPanel, …)
  pages/        Login, Patients, PatientDetail
  lib/          typed API client (api.ts) and shared types (types.ts)
  index.css     Tailwind theme tokens (light + dark)
```
