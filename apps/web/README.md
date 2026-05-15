# Alloha Web

Next.js frontend for the Alloha private MVP / technical case study.

The web app presents Alloha honestly as a real estate AI assistant MVP: lead qualification, property search, broker handoff, and a case-study page that discloses the current audit status.

## Current Positioning

- Private MVP / pilot-ready technical case study.
- Real estate AI assistant for WhatsApp-oriented lead workflows.
- RAG-ready architecture, not a claim of RAG running in the primary endpoint.
- No invented testimonials, customer logos, conversion metrics, or public production claims.

## Main Routes

- `/` - landing page with honest MVP positioning.
- `/case-study` - technical case study, audit metrics, architecture, implemented scope, and roadmap.
- `/blog` - content surface.
- `/contact` - contact/support lead capture.
- `/login`, `/signup`, `/setup`, `/dashboard` - app workflow surfaces.

## Tech Stack

- Next.js 16 with App Router.
- React 19 and TypeScript.
- Tailwind CSS.
- Framer Motion.
- Lucide React.
- Supabase client for auth/session-oriented frontend flows.

## Development

```bash
npm install
npm run dev --workspace=apps/web
```

Verification:

```bash
npm run lint --workspace=apps/web
npm run build --workspace=apps/web
```

## Content Rules

Keep the landing page aligned with the technical audit:

- Do not add fake customer logos, testimonials, or traction claims.
- Do not say RAG/vector search is live in the primary endpoint until it is connected and verified.
- Do not present the app as a public production SaaS.
- Do disclose the current MVP status, active listing count, embedding gap, and roadmap clearly.
