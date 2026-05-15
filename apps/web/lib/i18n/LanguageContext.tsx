"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Language = "en" | "pt-BR";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const translations: Record<Language, Record<string, string>> = {
  en: {
    "nav.about": "About",
    "nav.caseStudy": "Case study",
    "nav.blog": "Blog",
    "nav.features": "Features",
    "nav.pricing": "Pilot",
    "nav.faq": "FAQ",
    "nav.bookCall": "Request private demo",

    "hero.status": "Private MVP",
    "hero.statusDetail": "Pilot-ready technical case study",
    "hero.title1": "AI assistant for ",
    "hero.titleHighlight": "real estate leads",
    "hero.title2": "on WhatsApp",
    "hero.subtitle1": "Alloha is a private MVP that explores AI-powered ",
    "hero.subtitleHighlight": "lead qualification, property search,",
    "hero.subtitle2": " and broker handoff using FastAPI, Next.js, Supabase/PostgreSQL, Redis, and WhatsApp-oriented workflows.",
    "hero.ctaPrimary": "Request private demo",
    "hero.ctaSecondary": "View case study",

    "phone.online": "MVP assistant",
    "phone.chat1": "I need a 3-bedroom apartment near Batel",
    "phone.chat2": "I found matching listings in the property database.",
    "phone.chat3": "Want me to prepare a broker handoff?",
    "phone.chat4": "Yes, please send the details.",
    "phone.placeholder": "Type a lead message...",

    "bubble.online": "Alloha AI - pilot workflow",
    "bubble.message": "Lead intent captured. Property search and broker handoff are being prepared.",

    "stats.thisWeek": "Audit snapshot",
    "stats.measured": "Measured:",
    "stats.leads": "330 active listings",
    "stats.vsLastWeek": "0 embeddings filled",

    "proof.label": "Evidence",
    "proof.title": "Built as a technical",
    "proof.titleHighlight": "case study.",
    "proof.subtitle": "The landing now reflects the current engineering state: useful MVP architecture, clear gaps, and no inflated product claims.",
    "proof.card1.title": "330 active listings",
    "proof.card1.desc": "Measured in Supabase during the May 15, 2026 technical audit.",
    "proof.card2.title": "RAG-ready, not RAG-live",
    "proof.card2.desc": "pgvector/RPC 384d and RAG code exist, but the primary endpoints still use lexical search.",
    "proof.card3.title": "Known contract gap",
    "proof.card3.desc": "The API currently needs schema alignment before public production use.",

    "process.label": "Pilot flow",
    "process.title": "From inquiry to",
    "process.titleHighlight": "broker handoff.",
    "process.subtitle": "A practical workflow for testing AI-assisted real estate lead handling.",
    "process.step1.title": "Capture lead intent",
    "process.step1.desc": "Collect budget, location, property type, timing, and contact context from WhatsApp-style conversations.",
    "process.step2.title": "Search property data",
    "process.step2.desc": "Query the property database with filters today, with pgvector/RAG prepared as the next retrieval layer.",
    "process.step3.title": "Prepare handoff",
    "process.step3.desc": "Summarize lead qualification and candidate listings so a broker can follow up with context.",
    "process.cta": "View case study",

    "bento.visualize.title": "Property search",
    "bento.visualize.desc": "Filter listings by intent, neighborhood, price, and bedrooms.",
    "bento.brand.title": "Broker handoff",
    "bento.brand.desc": "Prepare structured lead context for a human follow-up.",
    "bento.multiplatform.title": "WhatsApp-oriented flow",
    "bento.multiplatform.desc": "Designed around conversational lead intake and response.",
    "bento.mockups.title": "RAG-ready architecture",
    "bento.mockups.desc": "Supabase/PostgreSQL with pgvector schema and RPC are included for semantic retrieval work.",
    "bento.internet.title": "Dashboard path",
    "bento.internet.desc": "Frontend routes exist for onboarding, setup, login, and operational screens.",

    "benefits.label": "What is implemented",
    "benefits.title": "Honest MVP",
    "benefits.titleHighlight": "scope.",
    "benefits.subtitle": "Alloha is positioned as a private technical MVP for validating real estate AI workflows, not as a scaled SaaS with invented traction.",
    "benefits.item1.title": "FastAPI backend",
    "benefits.item1.desc": "Canonical endpoints for chat, listing search, ingest, auth, onboarding, leads, and system status.",
    "benefits.item2.title": "Supabase data model",
    "benefits.item2.desc": "PostgreSQL schema includes properties, conversations, messages, leads, idempotency, and pgvector-ready fields.",
    "benefits.item3.title": "Model gateway",
    "benefits.item3.desc": "OpenRouter-oriented gateway with hard-stop behavior, rate limits, and Redis-backed metrics hooks.",
    "benefits.status.title": "Current audit status",
    "benefits.status.body": "The repo demonstrates a credible engineering direction, while the live data path still needs API/schema alignment and embedding backfill before semantic search claims are fair.",
    "benefits.status.meta": "Private MVP - May 2026 audit",

    "features.label": "Technical features",
    "features.title": "Designed for",
    "features.titleHighlight": "real estate workflows.",
    "features.subtitle": "A focused stack for lead qualification, property search, and future CRM-ready operations.",
    "features.designBoard.title": "Lead qualification",
    "features.designBoard.desc": "Extract budget, urgency, bedrooms, location, timing, and contact readiness from conversations.",
    "features.delivery.title": "Property search API",
    "features.delivery.desc": "Lexical and filter-based listing search is implemented as the current endpoint path.",
    "features.rate.title": "Guardrailed model gateway",
    "features.rate.desc": "Rate limits and hard-stop fallback avoid pretending the model layer is always available.",
    "features.designs.title": "pgvector schema",
    "features.designs.desc": "The repo includes vector(384) schema, indexes, and RPC for semantic retrieval work.",
    "features.revisions.title": "Ingest workflow",
    "features.revisions.desc": "Official feed first, scraper fallback, locking, change detection, and deactivation logic.",
    "features.unique.title": "Pilot dashboard",
    "features.unique.desc": "Next.js routes support login, onboarding, setup, dashboard, and contact flows.",
    "features.cta": "See GitHub",

    "solutions.label": "Coverage",
    "solutions.title": "A practical",
    "solutions.titleHighlight": "MVP surface",
    "solutions.title2": "for pilots.",
    "solutions.subtitle": "The product story is now limited to capabilities represented in the repository or audit findings.",
    "solutions.logos": "Lead qualification",
    "solutions.landingPages": "Property search",
    "solutions.websites": "WhatsApp conversations",
    "solutions.digitalProducts": "Broker handoff",
    "solutions.pitchDecks": "Property database",
    "solutions.mobileApps": "Dashboard",
    "solutions.emailDesign": "CRM-ready workflow",
    "solutions.productDesign": "Pilot onboarding",

    "pricing.label": "Pilot access",
    "pricing.title": "Private MVP,",
    "pricing.titleHighlight": "not public SaaS.",
    "pricing.subtitle": "Alloha is available as a technical case study and pilot conversation while core retrieval work is being completed.",
    "pricing.mostPopular": "PILOT READY",
    "pricing.pro.price": "Pilot",
    "pricing.pro.period": "",
    "pricing.pro.desc": "For recruiters, technical reviewers, and selected real estate pilot conversations.",
    "pricing.pro.feature1": "Private demo of the Next.js and FastAPI workflow",
    "pricing.pro.feature2": "Architecture walkthrough: Supabase, pgvector, Redis, WhatsApp flow",
    "pricing.pro.feature3": "Clear disclosure of current gaps and roadmap",
    "pricing.pro.feature4": "GitHub-visible technical case study",
    "pricing.pro.feature5": "No invented customer logos or vanity metrics",
    "pricing.pro.feature6": "Roadmap for embeddings, RAG, analytics, CRM, voice, and multi-tenant support",
    "pricing.pro.feature7": "Pilot discussion after API/schema contract fixes",
    "pricing.pro.cta": "Join pilot",
    "pricing.trial": "View case study",

    "faq.label": "FAQ",
    "faq.title": "Frequently asked",
    "faq.titleHighlight": "questions.",
    "faq.subtitle": "Straight answers about what Alloha is today.",
    "faq.q1": "Is Alloha a public production SaaS?",
    "faq.a1": "No. Alloha is a private MVP and technical case study. It is suitable for portfolio review and selected pilot conversations, not public production claims.",
    "faq.q2": "Does the main endpoint use RAG today?",
    "faq.a2": "No. The current /v1/listings/search path is lexical and filter-based, and /v1/chat/messages uses that path before calling the model gateway.",
    "faq.q3": "Is pgvector implemented?",
    "faq.a3": "The repo includes pgvector vector(384) schema, ivfflat indexes, and RPC for vector search. The audited database had 0 active listing embeddings filled.",
    "faq.q4": "What needs to be fixed next?",
    "faq.a4": "The priority is aligning the API with the real database schema, backfilling 384-dimensional embeddings, and connecting RAG retrieval to the primary chat/search flow.",
    "faq.q5": "Does the AI replace brokers?",
    "faq.a5": "No. The intended workflow is lead qualification, property search assistance, and broker handoff so a human can follow up with context.",
    "faq.q6": "Can I review the code?",
    "faq.a6": "Yes. The case study links to the GitHub repository and describes what is implemented, what was measured, and what remains on the roadmap.",

    "cta.title": "Review the",
    "cta.titleHighlight": "case study.",
    "cta.subtitle": "See the architecture, audit findings, implemented workflow, and next technical steps without inflated traction claims.",
    "cta.button": "View case study",
    "cta.note": "Private MVP - RAG-ready architecture - public-production gaps disclosed",

    "footer.privacy": "Privacy",
    "footer.terms": "Terms",
    "footer.contact": "Contact",
    "footer.rights": "© 2026 Alloha. Technical MVP case study.",
  },
  "pt-BR": {
    "nav.about": "Sobre",
    "nav.caseStudy": "Case study",
    "nav.blog": "Blog",
    "nav.features": "Recursos",
    "nav.pricing": "Piloto",
    "nav.faq": "FAQ",
    "nav.bookCall": "Solicitar demo privada",

    "hero.status": "MVP privado",
    "hero.statusDetail": "Case study técnico pronto para piloto",
    "hero.title1": "Assistente de IA para ",
    "hero.titleHighlight": "leads imobiliários",
    "hero.title2": "no WhatsApp",
    "hero.subtitle1": "Alloha é um MVP privado que explora ",
    "hero.subtitleHighlight": "qualificação de leads, busca de imóveis",
    "hero.subtitle2": " e repasse para corretores usando FastAPI, Next.js, Supabase/PostgreSQL, Redis e fluxos orientados ao WhatsApp.",
    "hero.ctaPrimary": "Solicitar demo privada",
    "hero.ctaSecondary": "Ver case study",

    "phone.online": "Assistente MVP",
    "phone.chat1": "Procuro apartamento de 3 quartos perto do Batel",
    "phone.chat2": "Encontrei imóveis compatíveis na base.",
    "phone.chat3": "Quer que eu prepare o repasse ao corretor?",
    "phone.chat4": "Sim, envie os detalhes.",
    "phone.placeholder": "Digite uma mensagem do lead...",

    "bubble.online": "Alloha AI - fluxo piloto",
    "bubble.message": "Intenção do lead capturada. Busca de imóveis e repasse ao corretor em preparação.",

    "stats.thisWeek": "Auditoria",
    "stats.measured": "Medido:",
    "stats.leads": "330 imóveis ativos",
    "stats.vsLastWeek": "0 embeddings preenchidos",

    "proof.label": "Evidências",
    "proof.title": "Construído como",
    "proof.titleHighlight": "case study técnico.",
    "proof.subtitle": "A landing agora reflete o estado real de engenharia: arquitetura útil de MVP, lacunas claras e nenhuma promessa inflada.",
    "proof.card1.title": "330 imóveis ativos",
    "proof.card1.desc": "Medidos no Supabase durante a auditoria técnica de 15 de maio de 2026.",
    "proof.card2.title": "RAG-ready, não RAG-live",
    "proof.card2.desc": "pgvector/RPC 384d e código de RAG existem, mas os endpoints principais ainda usam busca lexical.",
    "proof.card3.title": "Contrato a corrigir",
    "proof.card3.desc": "A API precisa de alinhamento com o schema antes de uso público em produção.",

    "process.label": "Fluxo piloto",
    "process.title": "Da consulta ao",
    "process.titleHighlight": "repasse ao corretor.",
    "process.subtitle": "Um fluxo prático para testar atendimento imobiliário assistido por IA.",
    "process.step1.title": "Capturar intenção",
    "process.step1.desc": "Coletar orçamento, localização, tipo de imóvel, prazo e contexto de contato em conversas estilo WhatsApp.",
    "process.step2.title": "Buscar imóveis",
    "process.step2.desc": "Consultar a base com filtros hoje, com pgvector/RAG preparado como próxima camada de recuperação.",
    "process.step3.title": "Preparar handoff",
    "process.step3.desc": "Resumir qualificação do lead e imóveis candidatos para o corretor seguir com contexto.",
    "process.cta": "Ver case study",

    "bento.visualize.title": "Busca de imóveis",
    "bento.visualize.desc": "Filtre imóveis por intenção, bairro, preço e quartos.",
    "bento.brand.title": "Repasse ao corretor",
    "bento.brand.desc": "Prepare contexto estruturado do lead para follow-up humano.",
    "bento.multiplatform.title": "Fluxo orientado ao WhatsApp",
    "bento.multiplatform.desc": "Desenhado para entrada e resposta conversacional de leads.",
    "bento.mockups.title": "Arquitetura RAG-ready",
    "bento.mockups.desc": "Supabase/PostgreSQL com schema pgvector e RPC para trabalho de busca semântica.",
    "bento.internet.title": "Caminho de dashboard",
    "bento.internet.desc": "Rotas de frontend existem para onboarding, setup, login e telas operacionais.",

    "benefits.label": "O que existe",
    "benefits.title": "Escopo honesto",
    "benefits.titleHighlight": "de MVP.",
    "benefits.subtitle": "Alloha é posicionado como MVP técnico privado para validar fluxos de IA imobiliária, não como SaaS escalado com tração inventada.",
    "benefits.item1.title": "Backend FastAPI",
    "benefits.item1.desc": "Endpoints canônicos para chat, busca de imóveis, ingestão, autenticação, onboarding, leads e status do sistema.",
    "benefits.item2.title": "Modelo de dados Supabase",
    "benefits.item2.desc": "Schema PostgreSQL com imóveis, conversas, mensagens, leads, idempotência e campos preparados para pgvector.",
    "benefits.item3.title": "Model gateway",
    "benefits.item3.desc": "Gateway orientado ao OpenRouter com hard-stop, limites de taxa e hooks de métricas via Redis.",
    "benefits.status.title": "Status da auditoria",
    "benefits.status.body": "O repo demonstra uma direção técnica crível, enquanto o caminho real de dados ainda precisa de alinhamento API/schema e backfill de embeddings antes de claims de busca semântica.",
    "benefits.status.meta": "MVP privado - auditoria de maio de 2026",

    "features.label": "Recursos técnicos",
    "features.title": "Desenhado para",
    "features.titleHighlight": "fluxos imobiliários.",
    "features.subtitle": "Uma stack focada em qualificação de leads, busca de imóveis e operações futuras conectadas ao CRM.",
    "features.designBoard.title": "Qualificação de leads",
    "features.designBoard.desc": "Extrai orçamento, urgência, quartos, localização, prazo e prontidão de contato das conversas.",
    "features.delivery.title": "API de busca de imóveis",
    "features.delivery.desc": "Busca lexical e por filtros está implementada como o caminho atual dos endpoints.",
    "features.rate.title": "Model gateway com limites",
    "features.rate.desc": "Rate limits e hard-stop evitam fingir que a camada de modelo está sempre disponível.",
    "features.designs.title": "Schema pgvector",
    "features.designs.desc": "O repo inclui schema vector(384), índices e RPC para trabalho de busca semântica.",
    "features.revisions.title": "Fluxo de ingestão",
    "features.revisions.desc": "Feed oficial primeiro, fallback de scraper, lock, detecção de mudanças e lógica de desativação.",
    "features.unique.title": "Dashboard piloto",
    "features.unique.desc": "Rotas Next.js dão suporte a login, onboarding, setup, dashboard e contato.",
    "features.cta": "Ver GitHub",

    "solutions.label": "Cobertura",
    "solutions.title": "Uma superfície",
    "solutions.titleHighlight": "MVP prática",
    "solutions.title2": "para pilotos.",
    "solutions.subtitle": "A narrativa do produto agora se limita a capacidades presentes no repositório ou na auditoria.",
    "solutions.logos": "Qualificação de leads",
    "solutions.landingPages": "Busca de imóveis",
    "solutions.websites": "Conversas WhatsApp",
    "solutions.digitalProducts": "Repasse ao corretor",
    "solutions.pitchDecks": "Base de imóveis",
    "solutions.mobileApps": "Dashboard",
    "solutions.emailDesign": "Fluxo CRM-ready",
    "solutions.productDesign": "Onboarding piloto",

    "pricing.label": "Acesso piloto",
    "pricing.title": "MVP privado,",
    "pricing.titleHighlight": "não SaaS público.",
    "pricing.subtitle": "Alloha está disponível como case study técnico e conversa de piloto enquanto o trabalho central de busca é concluído.",
    "pricing.mostPopular": "PILOTO",
    "pricing.pro.price": "Piloto",
    "pricing.pro.period": "",
    "pricing.pro.desc": "Para recrutadores, revisores técnicos e conversas selecionadas com imobiliárias piloto.",
    "pricing.pro.feature1": "Demo privada do fluxo Next.js e FastAPI",
    "pricing.pro.feature2": "Walkthrough de arquitetura: Supabase, pgvector, Redis, WhatsApp",
    "pricing.pro.feature3": "Divulgação clara de lacunas atuais e roadmap",
    "pricing.pro.feature4": "Case study técnico visível no GitHub",
    "pricing.pro.feature5": "Sem logos de clientes ou métricas de vaidade inventadas",
    "pricing.pro.feature6": "Roadmap para embeddings, RAG, analytics, CRM, voice e multi-tenant",
    "pricing.pro.feature7": "Conversa piloto após correção do contrato API/schema",
    "pricing.pro.cta": "Entrar no piloto",
    "pricing.trial": "Ver case study",

    "faq.label": "FAQ",
    "faq.title": "Perguntas",
    "faq.titleHighlight": "frequentes.",
    "faq.subtitle": "Respostas diretas sobre o que o Alloha é hoje.",
    "faq.q1": "Alloha é um SaaS público em produção?",
    "faq.a1": "Não. Alloha é um MVP privado e case study técnico. Serve para portfólio e conversas selecionadas de piloto, não para claims de produção pública.",
    "faq.q2": "O endpoint principal usa RAG hoje?",
    "faq.a2": "Não. O caminho atual /v1/listings/search é lexical e por filtros, e /v1/chat/messages usa esse caminho antes de chamar o model gateway.",
    "faq.q3": "pgvector está implementado?",
    "faq.a3": "O repo inclui schema pgvector vector(384), índices ivfflat e RPC para busca vetorial. O banco auditado tinha 0 embeddings preenchidos em imóveis ativos.",
    "faq.q4": "O que precisa ser corrigido agora?",
    "faq.a4": "A prioridade é alinhar a API com o schema real do banco, fazer backfill de embeddings 384d e conectar o retrieval RAG ao fluxo principal de chat/busca.",
    "faq.q5": "A IA substitui corretores?",
    "faq.a5": "Não. O fluxo pretendido é qualificação de leads, apoio na busca de imóveis e handoff para que o corretor humano siga com contexto.",
    "faq.q6": "Posso revisar o código?",
    "faq.a6": "Sim. O case study aponta para o repositório GitHub e descreve o que está implementado, o que foi medido e o que fica no roadmap.",

    "cta.title": "Revise o",
    "cta.titleHighlight": "case study.",
    "cta.subtitle": "Veja arquitetura, achados de auditoria, fluxo implementado e próximos passos técnicos sem claims inflados de tração.",
    "cta.button": "Ver case study",
    "cta.note": "MVP privado - arquitetura RAG-ready - lacunas de produção pública declaradas",

    "footer.privacy": "Privacidade",
    "footer.terms": "Termos",
    "footer.contact": "Contato",
    "footer.rights": "© 2026 Alloha. Case study técnico de MVP.",
  },
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const savedLang = localStorage.getItem("alloha-language") as Language;
    if (savedLang && (savedLang === "en" || savedLang === "pt-BR")) {
      setLanguageState(savedLang);
      return;
    }

    if (navigator.language.startsWith("pt")) {
      setLanguageState("pt-BR");
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("alloha-language", lang);
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
