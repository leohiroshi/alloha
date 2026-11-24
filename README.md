# Alloha

Private MVP / technical case study for a real estate AI assistant.

Alloha explores WhatsApp-oriented lead qualification, property search, and broker handoff workflows using a Next.js frontend, FastAPI backend, Supabase/PostgreSQL, Redis, and a model gateway. The repository includes a RAG-ready architecture and pgvector schema/RPC, but this is not presented as a public production SaaS.

The [local RAG demo](#local-rag-demo) runs against a synthetic property catalog and can evaluate retrieval and answers without credentials.

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
  rag_demo.py           Local property retrieval, generation, and evaluation
```

Core stack:

- Frontend: Next.js 16, React, TypeScript, Tailwind CSS, Framer Motion.
- Backend: Python 3.11, FastAPI, Supabase Python client.
- Data: Supabase/PostgreSQL with pgvector-ready schema.
- Workflow infra: Redis-compatible cache/lock/rate-limit hooks.
- AI integration: model gateway plus RAG-ready services.

## Local RAG Demo

From the repository root, use Python 3.11 or newer. The default run uses only the standard library, with weighted lexical retrieval and a deterministic answer from the top listing. It requires no accounts, downloads, or running services.

```bash
python scripts/rag_demo.py --query "apartamento com varanda" --neighborhood "Agua Verde" --transaction aluguel --max-price 3000
python scripts/rag_demo.py --eval --repeat 5 --report rag-report.json
```

The query returns an answer in Portuguese, the cited listing IDs, and retrieval and total latency. Neighborhood, transaction type, price ceiling, and `--required-feature` are hard filters; the question itself ranks the remaining listings. For example, appending `--required-feature piscina` to the query above returns no match. The catalog and labeled cases are in [`scripts/fixtures/rag_demo.json`](scripts/fixtures/rag_demo.json).

For semantic retrieval and generated answers, start [Ollama](https://docs.ollama.com/), download two local models, and rerun the same cases:

```bash
ollama pull embeddinggemma
ollama pull qwen2.5:3b
python scripts/rag_demo.py --eval --embed-model embeddinggemma --chat-model qwen2.5:3b --report rag-ollama.json
```

You can enable either model independently to compare semantic retrieval with lexical retrieval or generated answers with the deterministic baseline. Ollama runs on `127.0.0.1:11434` by default. `--top-k` and `--min-score` let you vary the retrieval depth and minimum cosine similarity. Use the same settings when comparing reports.

The report records Recall@K and mean reciprocal rank for retrieval, expected-fact and cited-ID checks for answers, the abstention rate for unsupported requests, and p50/p95 latency. The report includes per-case results and any token counts returned by Ollama. Latency excludes catalog indexing, which is reported separately. The script exits with status 1 if an answer check fails. Synthetic labels and text checks catch specific regressions but do not establish general factual accuracy.

The standard-library baseline has zero external API charges. Ollama execution depends on the models and machine used, so the report leaves provider cost unset in model mode. The demo runs independently of the deployed search and chat routes.

In a local run of the lexical baseline, all 13 synthetic cases passed over five repetitions (65 evaluations). Recall@3, the answer-check pass rate, and abstention on unsupported requests were each 100% on this fixture. These results describe the local baseline on the included catalog. The Ollama path was checked with simulated API responses; a model-quality benchmark is pending.

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
