import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Bot, Database, GitBranch, MessageSquare, Wrench } from "lucide-react";

export const metadata: Metadata = {
  title: "Alloha Case Study | Real Estate AI Assistant MVP",
  description:
    "Technical case study for Alloha, a private MVP exploring real estate lead qualification, property search, and broker handoff workflows.",
};

const auditMetrics = [
  { value: "330", label: "active listings measured in Supabase" },
  { value: "0", label: "active listings with embeddings filled during the audit" },
  { value: "384d", label: "pgvector/RPC dimension represented in the repo" },
  { value: "RAG-ready", label: "architecture present, not connected to primary endpoints yet" },
];

const architecture = [
  "Next.js App Router frontend for landing, auth, onboarding, setup, dashboard, and contact flows.",
  "FastAPI backend with canonical /v1 chat, listing search, ingest, lead, auth, and system status endpoints.",
  "Supabase/PostgreSQL data model for properties, conversations, messages, leads, idempotency, and vector-ready retrieval.",
  "pgvector vector(384) schema, ivfflat indexes, and RPC files included for semantic search work.",
  "Redis-backed hooks for sessions, rate limits, idempotency, model metrics, and ingest locking.",
  "WhatsApp-oriented workflow design and model gateway for assisted lead conversations.",
];

const implemented = [
  "Real estate landing and dashboard-oriented Next.js app structure.",
  "FastAPI core API with chat, listings, ingest, leads, auth, onboarding, and health/status routes.",
  "Property ingest service with feed-first behavior, scraper fallback hooks, content hashes, and deactivation logic.",
  "Model gateway with hard-stop behavior, rate limits, provider metadata, and capacity-limited responses.",
  "Supabase schema and migrations for property data, conversations, leads, messages, and pgvector-ready retrieval.",
  "Benchmark script for measuring counts, endpoint latency, error rate, and vector retrieval behavior without exposing secrets.",
];

const roadmap = [
  "Correct the API/database contract for listing fields used by /v1/listings/search and /v1/chat/messages.",
  "Backfill 384-dimensional property embeddings for active listings.",
  "Connect RAG/vector retrieval to the primary search and chat flow.",
  "Add analytics for lead source, response quality, broker handoff, and search relevance.",
  "Build CRM-ready lead states, assignment, notes, and follow-up workflow.",
  "Expand voice, multimodal intake, and WhatsApp media handling after the core data path is stable.",
  "Harden multi-tenant onboarding, permissions, observability, and deployment operations.",
];

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-white/10 py-14">
      <h2 className="text-2xl md:text-3xl font-semibold text-white mb-6">{title}</h2>
      {children}
    </section>
  );
}

export default function CaseStudyPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <nav className="flex items-center justify-between gap-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-white/60 hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Back to landing
          </Link>
          <a
            href="https://github.com/leohiroshi/alloha"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-sm text-white/75 hover:border-[#FF5500]/50 hover:text-white"
          >
            GitHub
            <ArrowUpRight className="h-4 w-4" />
          </a>
        </nav>

        <header className="py-20 md:py-28">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#FF5500]/25 bg-[#FF5500]/10 px-4 py-2 text-sm text-[#ffb080]">
            <Bot className="h-4 w-4" />
            Private MVP / technical case study
          </div>
          <h1 className="max-w-4xl text-5xl md:text-7xl font-bold tracking-tight">
            AI assistant for real estate leads on WhatsApp
          </h1>
          <p className="mt-8 max-w-3xl text-lg md:text-xl leading-8 text-white/62">
            Alloha explores AI-powered lead qualification, property search, and broker handoff using
            FastAPI, Next.js, Supabase/PostgreSQL, Redis, pgvector, WhatsApp-oriented workflows, and a
            guardrailed model gateway.
          </p>
          <p className="mt-5 max-w-3xl text-base leading-7 text-white/45">
            Status: private MVP and pilot case study. It is not a public production SaaS, and the
            current audit findings are disclosed below.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-4 pb-14">
          {auditMetrics.map((metric) => (
            <div key={metric.label} className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
              <div className="text-3xl font-semibold text-white">{metric.value}</div>
              <p className="mt-3 text-sm leading-6 text-white/50">{metric.label}</p>
            </div>
          ))}
        </section>

        <Section title="Problem">
          <p className="max-w-3xl text-white/62 leading-8">
            Real estate teams often lose leads outside business hours and struggle to respond quickly
            with relevant property options. A broker needs enough context to qualify the lead, answer
            property questions, and decide the next follow-up without reading a long raw conversation.
          </p>
        </Section>

        <Section title="Solution">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                icon: MessageSquare,
                title: "Lead qualification",
                body: "Capture budget, location, bedrooms, timing, urgency, and contact intent from conversational messages.",
              },
              {
                icon: Database,
                title: "Property search",
                body: "Use the property database to prepare relevant listing suggestions and move toward semantic retrieval.",
              },
              {
                icon: GitBranch,
                title: "Broker handoff",
                body: "Summarize the lead and candidate properties so a broker can follow up with context.",
              },
            ].map((item) => (
              <div key={item.title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                <item.icon className="h-6 w-6 text-[#FF5500]" />
                <h3 className="mt-5 text-lg font-semibold">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-white/50">{item.body}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Architecture">
          <ul className="grid gap-3 md:grid-cols-2">
            {architecture.map((item) => (
              <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.025] p-4 text-sm leading-6 text-white/58">
                {item}
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Audit Status">
          <div className="rounded-3xl border border-[#FF5500]/20 bg-[#FF5500]/10 p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="mt-1 rounded-full bg-[#FF5500]/15 p-3">
                <Wrench className="h-5 w-5 text-[#FF5500]" />
              </div>
              <div>
                <h3 className="text-xl font-semibold">Honest current state</h3>
                <p className="mt-4 max-w-3xl text-white/62 leading-8">
                  The May 15, 2026 audit found 330 active properties in Supabase and 0 active
                  properties with embeddings filled. The repo includes pgvector/RPC 384d and RAG
                  code, but the primary endpoints still use lexical search and filters. The main
                  listing/chat endpoints need an API/schema contract correction before public use.
                </p>
              </div>
            </div>
          </div>
        </Section>

        <Section title="Implemented">
          <ul className="grid gap-3 md:grid-cols-2">
            {implemented.map((item) => (
              <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.025] p-4 text-sm leading-6 text-white/58">
                {item}
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Roadmap">
          <ol className="grid gap-3">
            {roadmap.map((item, index) => (
              <li key={item} className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.025] p-4 text-sm leading-6 text-white/58">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#FF5500]/15 text-xs font-semibold text-[#FF5500]">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
        </Section>

        <section className="border-t border-white/10 py-16">
          <div className="rounded-[32px] border border-white/10 bg-gradient-to-b from-white/[0.07] to-white/[0.02] p-8 md:p-12">
            <h2 className="text-3xl md:text-4xl font-semibold">Review the repository</h2>
            <p className="mt-4 max-w-2xl text-white/58 leading-7">
              The best way to evaluate Alloha is as an engineering portfolio project: read the code,
              inspect the architecture, and compare the roadmap against the audit findings.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <a
                href="https://github.com/leohiroshi/alloha"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#FF5500] px-6 py-3 font-semibold text-black hover:bg-[#FF6600]"
              >
                See GitHub
                <ArrowUpRight className="h-4 w-4" />
              </a>
              <Link
                href="/contact"
                className="inline-flex items-center justify-center rounded-full border border-white/15 px-6 py-3 font-semibold text-white/80 hover:border-white/35 hover:text-white"
              >
                Request private demo
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
