# Alloha

Private MVP / technical case study for a real estate AI assistant.

Alloha explores WhatsApp-oriented lead qualification, property search, and broker handoff workflows using a Next.js frontend, FastAPI backend, Supabase/PostgreSQL, Redis, and a model gateway. The repository includes a RAG-ready architecture and pgvector schema/RPC, but this is not presented as a public production SaaS.

## Current Status

This project is best evaluated as a technical portfolio case study and private pilot candidate.

Audit snapshot from May 15, 2026:

- 330 active properties measured in Supabase.
- 0 active properties had embeddings filled at the time of the audit.
- The repo includes pgvector `vector(384)` schema/RPC and RAG pipeline code.
- The primary endpoints currently use lexical search and filters, not connected RAG/vector retrieval.
- `/v1/listings/search` is the current lexical/filter listing search path.
- `/v1/chat/messages` calls the lexical listing search path before the model gateway.
- The audited live data path needs API/schema contract alignment before public use.

## What This Repo Demonstrates

- Real estate AI assistant workflow design.
- FastAPI backend with chat, listings, ingest, auth, onboarding, leads, and system status routes.
- Supabase/PostgreSQL schema for properties, conversations, messages, leads, idempotency, and vector-ready retrieval.
- pgvector-ready SQL with `vector(384)`, ivfflat indexes, and RPC files.
- Redis-backed patterns for sessions, rate limiting, idempotency, metrics, and ingest locks.
- Next.js landing, auth, onboarding, setup, dashboard, contact, and case-study surfaces.
- Benchmark tooling for counts, latency, error rate, and vector retrieval checks without printing secrets.

## What This Repo Does Not Claim

- It is not a public production SaaS.
- It does not claim thousands of users, customer logos, conversion lift, or production RAG.
- It does not claim active property embeddings are already populated.
- It does not claim the primary endpoint currently performs semantic vector search.

## Architecture

```text
apps/
  api/          FastAPI backend, Supabase client, ingest, model gateway, RAG-related services
  web/          Next.js app, landing, case study, auth/onboarding/dashboard surfaces
packages/
  shared/       Shared workspace package area
scripts/
  benchmark_alloha.py  Technical audit and benchmark helper
```

Core stack:

- Frontend: Next.js 16, React, TypeScript, Tailwind CSS, Framer Motion.
- Backend: Python 3.11, FastAPI, Supabase Python client.
- Data: Supabase/PostgreSQL with pgvector-ready schema.
- Workflow infra: Redis-compatible cache/lock/rate-limit hooks.
- AI integration: model gateway plus RAG-ready services.

## Local Development

```bash
npm install

cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run services:

```bash
npm run dev:web
npm run dev:api
```

Useful checks:

```bash
npm run lint --workspace=apps/web
npm run build --workspace=apps/web
.venv\Scripts\python.exe scripts\benchmark_alloha.py --help
```

## Roadmap

- Correct the API/database contract for listing fields.
- Backfill 384-dimensional property embeddings.
- Connect RAG/vector retrieval to the primary search and chat flow.
- Add search relevance analytics and lead funnel metrics.
- Build CRM-ready lead state, broker assignment, notes, and follow-up flows.
- Expand voice and WhatsApp media handling after the core data path is stable.
- Harden multi-tenant onboarding, permissions, observability, and deployment operations.

## License

MIT
