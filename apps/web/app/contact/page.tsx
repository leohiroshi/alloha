"use client";

import type { FormEvent, ReactNode } from "react";
import { useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Clock3, FileText, LifeBuoy, WalletCards, type LucideIcon } from "lucide-react";
import api from "@/lib/api";

type SupportCardConfig = {
  title: string;
  body: string;
  cta: string;
  presetTopic: string;
  presetInterest: string;
  icon: LucideIcon;
};

const navLinks = [
  { href: "/login?mode=signup", label: "Começar" },
  { href: "/blog", label: "Recursos" },
  { href: "/privacy", label: "Privacidade" },
  { href: "/terms", label: "Termos" },
];

const supportCards: SupportCardConfig[] = [
  {
    title: "Suporte do MVP",
    body: "Use o formulário para relatar qualquer bloqueio de ativação, configuração ou uso inicial.",
    cta: "Preencher formulário",
    presetTopic: "Suporte do MVP",
    presetInterest: "Preciso de ajuda com configuração, onboarding ou operação inicial.",
    icon: LifeBuoy,
  },
  {
    title: "Financeiro",
    body: "Envie por aqui dúvidas sobre plano, cobrança, renovação ou ajustes comerciais.",
    cta: "Preencher formulário",
    presetTopic: "Financeiro",
    presetInterest: "Preciso de ajuda com cobrança, plano ou condição comercial.",
    icon: WalletCards,
  },
  {
    title: "Comercial",
    body: "Se quiser falar sobre proposta, implantação ou escopo inicial, este é o canal certo.",
    cta: "Preencher formulário",
    presetTopic: "Comercial",
    presetInterest: "Quero entender proposta, implantação e próximos passos comerciais.",
    icon: FileText,
  },
];

const footerColumns = [
  {
    title: "Produto",
    links: [
      { href: "/", label: "Landing" },
      { href: "/login?mode=signup", label: "Primeiro acesso" },
      { href: "/login", label: "Entrar" },
      { href: "/dashboard", label: "Dashboard" },
    ],
  },
  {
    title: "Recursos",
    links: [
      { href: "/blog", label: "Blog" },
      { href: "/contact", label: "Contato" },
      { href: "/privacy", label: "Privacidade" },
      { href: "/terms", label: "Termos" },
    ],
  },
  {
    title: "Conta",
    links: [
      { href: "/login", label: "Entrar" },
      { href: "/signup", label: "Cadastrar" },
      { href: "/login?mode=signup", label: "Abrir onboarding" },
      { href: "/contact", label: "Falar com suporte" },
    ],
  },
  {
    title: "Ajuda",
    links: [
      { href: "#lead-form", label: "Abrir formulário" },
      { href: "/blog/primeiro-mvp-sem-cron", label: "MVP sem cron" },
      { href: "/blog/checklist-antes-de-publicar", label: "Checklist" },
      { href: "/privacy", label: "Privacidade" },
    ],
  },
];

export default function ContactPage() {
  const formSectionRef = useRef<HTMLDivElement | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [interest, setInterest] = useState("");
  const [topic, setTopic] = useState("Contato geral");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const focusForm = (nextTopic: string, nextInterest: string) => {
    setTopic(nextTopic);
    setInterest(nextInterest);
    setMessage(null);
    setError(null);
    formSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const result = await api.createLead({
        name,
        phone,
        email: email || undefined,
        topic,
        interest: interest || undefined,
      });

      if (result.success) {
        setMessage(result.message || "Seu suporte foi processado. Vamos avaliar e entraremos em contato.");
        setName("");
        setPhone("");
        setEmail("");
        setInterest("");
        setTopic("Contato geral");
      } else {
        setError("Não foi possível enviar o contato.");
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Falha ao enviar contato.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#040404] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-5%,rgba(255,120,40,0.14),transparent_28%),linear-gradient(180deg,#050505_0%,#040404_45%,#020202_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.024)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.024)_1px,transparent_1px)] bg-[size:64px_64px] opacity-20" />
        <div className="absolute left-0 right-0 top-[78px] h-px bg-gradient-to-r from-transparent via-white/16 to-transparent" />
      </div>

      <div className="relative z-10">
        <header className="sticky top-0 z-40 border-b border-white/8 bg-black/70 backdrop-blur-2xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <Link href="/" className="flex min-h-11 items-center gap-3">
              <Image src="/logo.png" alt="Alloha" width={28} height={28} />
              <div className="leading-none">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-white">Alloha</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.28em] text-white/40">real estate ai</p>
              </div>
            </Link>

            <nav className="hidden items-center gap-5 lg:flex">
              {navLinks.map((link) => (
                <Link key={link.href} href={link.href} className="text-sm text-white/62 transition hover:text-white">
                  {link.label}
                </Link>
              ))}
            </nav>

            <div className="flex items-center gap-3">
              <Link href="/login" className="aw-btn-secondary min-h-11 px-4 py-3 text-sm">
                Entrar
              </Link>
              <Link href="/login?mode=signup" className="aw-btn-primary min-h-11 px-5 py-3 text-sm">
                Começar
              </Link>
            </div>
          </div>
        </header>

        <section className="mx-auto max-w-4xl px-4 pb-12 pt-16 text-center sm:px-6 lg:px-8 lg:pt-24">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-[11px] uppercase tracking-[0.24em] text-white/58">
            <span className="h-2 w-2 rounded-full bg-[#ff7b2c]" />
            Contato
          </div>
          <h1 className="mt-8 text-5xl font-semibold tracking-[-0.06em] text-white sm:text-6xl lg:text-7xl">Contato</h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-white/58 sm:text-xl">
            Por enquanto, todo suporte entra por este formulário. A solicitação chega em <span className="text-white">contato@alloha.app</span> e nossa equipe responde após a análise.
          </p>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-18 sm:px-6 lg:px-8">
          <div className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl sm:p-8 lg:p-10">
            <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-[#ff8f4d]/18 bg-[#ff5500]/8 px-3 py-1.5 text-[11px] uppercase tracking-[0.22em] text-[#ffc8a6]">
                  Canal único de suporte
                </div>
                <h2 className="mt-6 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">
                  Um único canal, com menos ruído e mais clareza.
                </h2>
                <p className="mt-4 max-w-2xl text-base leading-8 text-white/58">
                  Concentramos tudo em um fluxo simples para manter o atendimento organizado neste primeiro MVP. Você escolhe o assunto, envia a mensagem e a equipe segue a partir daí.
                </p>
              </div>

              <div className="flex flex-col items-start gap-4 lg:items-end">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-white/70">
                  <span className="h-2 w-2 rounded-full bg-[#ff7b2c]" />
                  contato@alloha.app
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => focusForm("Contato geral", "Quero falar com a equipe Alloha.")}
                    className="aw-btn-primary"
                  >
                    Abrir formulário
                  </button>
                  <Link href="/privacy" className="aw-btn-secondary">
                    Política de privacidade
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-3">
            {supportCards.map((card) => {
              const Icon = card.icon;
              return (
                <section
                  key={card.title}
                  className="rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,14,14,0.96),rgba(8,8,8,0.98))] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.2)]"
                >
                  <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#ff8d48]/16 bg-[#ff5500]/10 text-[#ffbe95]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-6 text-2xl font-semibold tracking-[-0.03em] text-white">{card.title}</h3>
                  <p className="mt-3 text-base leading-7 text-white/56">{card.body}</p>
                  <button
                    type="button"
                    onClick={() => focusForm(card.presetTopic, card.presetInterest)}
                    className="aw-btn-secondary mt-8 w-fit px-4 py-2 text-sm"
                  >
                    {card.cta}
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </section>
              );
            })}
          </div>
        </section>

        <section ref={formSectionRef} id="lead-form" className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)]">
            <section className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))] p-6 sm:p-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] uppercase tracking-[0.22em] text-white/56">
                Fluxo ativo
              </div>
              <h2 className="mt-6 text-3xl font-semibold tracking-[-0.04em] text-white">Abrir ticket</h2>
              <p className="mt-4 text-base leading-8 text-white/58">
                O formulário é enxuto e direto. Se você informar seu e-mail, também enviamos uma confirmação de recebimento.
              </p>

              <div className="mt-8 space-y-4">
                <InfoLine label="Assunto" value={topic} />
                <InfoLine label="Destino" value="contato@alloha.app" />
                <InfoLine label="Retorno" value="analisamos cada solicitação e respondemos pelo canal informado" />
              </div>

              <div className="mt-8 rounded-[22px] border border-[#ff8d48]/16 bg-[#ff5500]/8 p-4 text-sm leading-7 text-[#ffe6d8]">
                Mesmo se a confirmação por e-mail falhar, sua solicitação continua registrada e segue para análise da equipe.
              </div>
            </section>

            <section className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,14,14,0.98),rgba(8,8,8,1))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.26)] sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/42">Formulário de suporte</p>
                  <h3 className="mt-3 text-2xl font-semibold text-white">Fale com a equipe</h3>
                </div>
                <div className="inline-flex items-center gap-2 rounded-full border border-[#ff8d48]/16 bg-[#ff5500]/10 px-3 py-1.5 text-xs font-medium text-[#ffc6a1]">
                  <Clock3 className="h-4 w-4" />
                  {topic}
                </div>
              </div>

              <form onSubmit={onSubmit} className="mt-8 grid gap-4 md:grid-cols-2">
                <Field label="Nome" helper="Como devemos chamar você?">
                  <input required value={name} onChange={(event) => setName(event.target.value)} className="liquid-input" />
                </Field>

                <Field label="Telefone" helper="Canal principal para retorno.">
                  <input required value={phone} onChange={(event) => setPhone(event.target.value)} className="liquid-input" />
                </Field>

                <Field label="E-mail" helper="Opcional, mas recomendado para receber confirmação." className="md:col-span-2">
                  <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="liquid-input" />
                </Field>

                <Field label="Mensagem" helper="Descreva o contexto do suporte ou ajuste o texto sugerido." className="md:col-span-2">
                  <textarea
                    value={interest}
                    onChange={(event) => setInterest(event.target.value)}
                    rows={5}
                    className="liquid-input min-h-[152px] resize-none"
                  />
                </Field>

                <div className="md:col-span-2 flex flex-wrap gap-3">
                  <button type="submit" disabled={loading} className="aw-btn-primary">
                    {loading ? "Enviando..." : "Enviar suporte"}
                  </button>
                  <Link href="/privacy" className="aw-btn-secondary">
                    Política de privacidade
                  </Link>
                  <Link href="/terms" className="aw-btn-secondary">
                    Termos de uso
                  </Link>
                </div>
              </form>

              {message ? (
                <div className="mt-6 rounded-[24px] border border-[#ffb47c]/20 bg-[#ff7a26]/10 p-4 text-sm leading-7 text-[#ffe7da]">
                  {message}
                </div>
              ) : null}

              {error ? (
                <div className="mt-6 rounded-[24px] border border-[#ff9357]/25 bg-[#ff5a1f]/10 p-4 text-sm leading-7 text-[#ffd7c7]">
                  {error}
                </div>
              ) : null}
            </section>
          </div>
        </section>

        <footer className="border-t border-white/8 bg-black/82">
          <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.2fr_2fr] lg:px-8">
            <div>
              <div className="flex items-center gap-3">
                <Image src="/logo.png" alt="Alloha" width={30} height={30} />
                <div>
                  <p className="text-xl font-semibold uppercase tracking-[0.16em] text-white">Alloha</p>
                  <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">real estate ai</p>
                </div>
              </div>
              <p className="mt-6 max-w-sm text-sm leading-7 text-white/56">
                Atendimento imobiliário com IA, onboarding simples e um único canal público de suporte para o primeiro MVP.
              </p>
              <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-white/68">
                <span className="h-2 w-2 rounded-full bg-[#ff7b2c]" />
                Suporte via formulário para contato@alloha.app
              </div>
            </div>

            <div className="grid gap-8 sm:grid-cols-2 xl:grid-cols-4">
              {footerColumns.map((column) => (
                <div key={column.title}>
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#ffb177]">{column.title}</p>
                  <div className="mt-5 space-y-3">
                    {column.links.map((link) => (
                      <Link key={link.href + link.label} href={link.href} className="block text-sm text-white/54 transition hover:text-white">
                        {link.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}

function Field({
  label,
  helper,
  children,
  className = "",
}: {
  label: string;
  helper: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className}`.trim()}>
      <span className="mb-2 block text-sm font-medium text-white/86">{label}</span>
      {children}
      <span className="mt-2 block text-xs leading-6 text-white/46">{helper}</span>
    </label>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-white/8 bg-white/[0.03] px-4 py-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-white/38">{label}</p>
      <p className="mt-2 text-sm leading-7 text-white/78">{value}</p>
    </div>
  );
}
