"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  CircleDashed,
  LoaderCircle,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { clearAllohaAuth, resolveAuthenticatedSession } from "@/lib/auth-session";
import api from "@/lib/api";
import {
  loadMetaEmbeddedSignupSdk,
  META_EMBEDDED_SIGNUP_ALLOWED_ORIGINS,
  parseMetaEmbeddedSignupMessage,
} from "@/lib/meta-embedded-signup";

type Profile = {
  sub?: string;
  name?: string;
  email?: string;
  picture?: string;
  provider?: string;
};

type OnboardingStatus = {
  configured: boolean;
  ingest_in_progress: boolean;
  first_scrape_completed: boolean;
  first_scrape_started_at?: string;
  whatsapp?: {
    provider?: string;
    connected?: boolean;
    embedded_signup_ready?: boolean;
    app_id?: string | null;
    embedded_signup_config_id?: string | null;
    token_exchange_ready?: boolean;
    js_sdk_version?: string | null;
    current_phone_number_id?: string | null;
    next_step_url?: string | null;
  };
  whatsapp_signup?: {
    event?: string;
    source?: string;
    captured_at?: string;
    code_received?: boolean;
    token_exchange_ready?: boolean;
    waba_id?: string | null;
    phone_number_id?: string | null;
    display_phone_number?: string | null;
    session_id?: string | null;
    current_step?: string | null;
    error_message?: string | null;
    error_id?: string | null;
  } | null;
  config?: {
    business_name?: string;
    owner_name?: string;
    whatsapp_phone?: string;
    whatsapp_number_mode?: string;
    city?: string;
    website_url?: string;
  };
  site_inspection?: {
    provided?: boolean;
    normalized_url?: string;
    reachable?: boolean;
    http_status?: number | null;
    final_url?: string | null;
    host?: string | null;
    page_title?: string | null;
    platform_hint?: string | null;
    scrape_supported?: boolean;
    recommended_source?: string;
    ready_for_ingest?: boolean;
    message?: string;
  } | null;
  last_result?: {
    success?: boolean;
    message?: string;
    error?: string;
    inserted_or_updated?: number;
    total_seen?: number;
  } | null;
};

type StepState = "pending" | "active" | "done";

function formatTimestamp(value?: string) {
  if (!value) {
    return "Ainda não iniciado";
  }

  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatRecommendedSource(value?: string) {
  switch (value) {
    case "official_feed":
      return "Fonte oficial";
    case "scraper_fallback":
      return "Scraper compatível";
    case "scraper_supported_but_disabled":
      return "Scraper compatível, mas desligado";
    case "manual_review":
      return "Revisão manual";
    case "site_required":
      return "Site obrigatório";
    default:
      return "Aguardando validação";
  }
}

function formatMetaEvent(value?: string) {
  switch (value) {
    case "FINISH":
      return "Concluído";
    case "CANCEL":
      return "Cancelado";
    case "ERROR":
      return "Erro";
    case "CODE_RECEIVED":
      return "Código recebido";
    default:
      return value || "Sem retorno";
  }
}

export default function DashboardPage() {
  const router = useRouter();
  const [sessionToken, setSessionToken] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [businessName, setBusinessName] = useState("Alloha Imóveis");
  const [ownerName, setOwnerName] = useState("Equipe Alloha");
  const [whatsappPhone, setWhatsappPhone] = useState("");
  const [whatsappNumberMode, setWhatsappNumberMode] = useState<"existing" | "new">("existing");
  const [city, setCity] = useState("São Paulo");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [metaBusy, setMetaBusy] = useState(false);
  const [metaSdkReady, setMetaSdkReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const whatsappSetup = status?.whatsapp || null;
  const whatsappSignup = status?.whatsapp_signup || null;

  useEffect(() => {
    const load = async () => {
      const resolved = await resolveAuthenticatedSession();
      if (!resolved) {
        router.replace("/login");
        return;
      }

      setSessionToken(resolved.token);

      try {
        const [defaultsResponse, statusResponse] = await Promise.all([
          api.getOnboardingDefaults(resolved.token),
          api.getOnboardingStatus(resolved.token),
        ]);

        const nextProfile = resolved.profile || null;
        const config = statusResponse.config || defaultsResponse.defaults;

        setProfile(nextProfile);
        setStatus(statusResponse);
        setBusinessName(config.business_name || defaultsResponse.defaults.business_name);
        setOwnerName(config.owner_name || nextProfile?.name || defaultsResponse.defaults.owner_name);
        setWhatsappPhone(config.whatsapp_phone || defaultsResponse.defaults.whatsapp_phone);
        setWhatsappNumberMode(
          (config.whatsapp_number_mode as "existing" | "new") ||
            (defaultsResponse.defaults.whatsapp_number_mode as "existing" | "new") ||
            "existing"
        );
        setCity(config.city || defaultsResponse.defaults.city);
        setWebsiteUrl(config.website_url || defaultsResponse.defaults.website_url);
      } catch (currentError) {
        const nextError = currentError instanceof Error ? currentError.message : "Não foi possível carregar o painel.";
        if (nextError.toLowerCase().includes("session") || nextError.toLowerCase().includes("auth token")) {
          await clearAllohaAuth();
          router.replace("/login");
          return;
        }
        setError(nextError);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [router]);

  useEffect(() => {
    if (!sessionToken || !status?.ingest_in_progress) {
      return;
    }

    const interval = setInterval(() => {
      void (async () => {
        try {
          const nextStatus = await api.getOnboardingStatus(sessionToken);
          setStatus(nextStatus);
        } catch (currentError) {
          setError(currentError instanceof Error ? currentError.message : "Não foi possível atualizar o status.");
        }
      })();
    }, 3000);

    return () => clearInterval(interval);
  }, [sessionToken, status?.ingest_in_progress]);

  useEffect(() => {
    if (!whatsappSetup?.app_id || !whatsappSetup?.embedded_signup_config_id) {
      setMetaSdkReady(false);
      return;
    }

    let cancelled = false;
    void loadMetaEmbeddedSignupSdk(
      whatsappSetup.app_id,
      whatsappSetup.js_sdk_version || "v23.0"
    )
      .then(() => {
        if (!cancelled) {
          setMetaSdkReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMetaSdkReady(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    whatsappSetup?.app_id,
    whatsappSetup?.embedded_signup_config_id,
    whatsappSetup?.js_sdk_version,
  ]);

  useEffect(() => {
    if (!sessionToken) {
      return;
    }

    const handleMetaMessage = (event: MessageEvent) => {
      if (!META_EMBEDDED_SIGNUP_ALLOWED_ORIGINS.includes(event.origin)) {
        return;
      }

      const payload = parseMetaEmbeddedSignupMessage(event.data);
      if (!payload) {
        return;
      }

      setMetaBusy(false);
      void (async () => {
        try {
          const result = await api.saveWhatsAppEmbeddedSignup(
            {
              event: String(payload.event || "MESSAGE_EVENT"),
              data:
                payload.data && typeof payload.data === "object"
                  ? (payload.data as Record<string, unknown>)
                  : {},
              raw: payload,
              source: "meta_post_message",
            },
            sessionToken
          );
          const nextStatus = await api.getOnboardingStatus(sessionToken);
          setStatus(nextStatus);
          setMessage(result.message);
        } catch (currentError) {
          setError(
            currentError instanceof Error
              ? currentError.message
              : "Não foi possível processar o retorno da Meta."
          );
        }
      })();
    };

    window.addEventListener("message", handleMetaMessage);
    return () => window.removeEventListener("message", handleMetaMessage);
  }, [sessionToken]);

  const handleLogout = async () => {
    await clearAllohaAuth();
    router.replace("/login");
  };

  const handleSubmit = async () => {
    if (!sessionToken) {
      router.replace("/login");
      return;
    }

    if (!websiteUrl.trim()) {
      setError("Informe a URL do site da imobiliária antes de continuar.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      const result = await api.bootstrapOnboarding(
        {
          business_name: businessName,
          owner_name: ownerName,
          whatsapp_phone: whatsappPhone,
          whatsapp_number_mode: whatsappNumberMode,
          city,
          website_url: websiteUrl,
          force_full_scrape: true,
        },
        sessionToken
      );
      const nextStatus = await api.getOnboardingStatus(sessionToken);
      setStatus(nextStatus);
      setMessage(result.message);
    } catch (currentError) {
      const nextError = currentError instanceof Error ? currentError.message : "Não foi possível iniciar o onboarding.";
      if (nextError.toLowerCase().includes("session") || nextError.toLowerCase().includes("auth token")) {
        await clearAllohaAuth();
        router.replace("/login");
        return;
      }
      setError(nextError);
    } finally {
      setSubmitting(false);
    }
  };

  const handleLaunchMetaSignup = async () => {
    if (!sessionToken) {
      router.replace("/login");
      return;
    }

    if (!whatsappSetup?.app_id || !whatsappSetup?.embedded_signup_config_id) {
      setError("As chaves do Embedded Signup da Meta ainda não estão completas neste ambiente.");
      return;
    }

    setMetaBusy(true);
    setError(null);
    setMessage(null);

    try {
      await loadMetaEmbeddedSignupSdk(
        whatsappSetup.app_id,
        whatsappSetup.js_sdk_version || "v23.0"
      );
      setMetaSdkReady(true);

      if (!window.FB) {
        throw new Error("O SDK da Meta foi carregado, mas não ficou disponível na página.");
      }

      window.FB.login(
        async (response) => {
          try {
            const code =
              response &&
              typeof response === "object" &&
              "authResponse" in response &&
              response.authResponse &&
              typeof response.authResponse === "object" &&
              "code" in response.authResponse
                ? response.authResponse.code
                : null;

            if (typeof code === "string" && code.trim()) {
              const result = await api.saveWhatsAppEmbeddedSignup(
                {
                  event: "CODE_RECEIVED",
                  code,
                  data: {},
                  source: "meta_login_callback",
                },
                sessionToken
              );
              const nextStatus = await api.getOnboardingStatus(sessionToken);
              setStatus(nextStatus);
              setMessage(result.message);
            } else {
              setMessage("Fluxo da Meta iniciado. O painel será atualizado assim que houver retorno.");
            }
          } catch (currentError) {
            setError(
              currentError instanceof Error
                ? currentError.message
                : "Não foi possível salvar o retorno da Meta."
            );
          } finally {
            setMetaBusy(false);
          }
        },
        {
          config_id: whatsappSetup.embedded_signup_config_id,
          response_type: "code",
          override_default_response_type: true,
          extras: {
            setup: {},
          },
        }
      );
    } catch (currentError) {
      setMetaBusy(false);
      setError(
        currentError instanceof Error
          ? currentError.message
          : "Não foi possível abrir o fluxo oficial da Meta."
      );
    }
  };

  const hasConfigured = Boolean(status?.configured);
  const isRunning = Boolean(status?.ingest_in_progress);
  const isCompleted = Boolean(status?.first_scrape_completed && status?.last_result?.success);
  const isFailed = Boolean(status?.last_result && status.last_result.success === false);
  const siteInspection = status?.site_inspection || null;
  const siteReadyForIngest = Boolean(siteInspection?.ready_for_ingest);
  const canSubmit = Boolean(websiteUrl.trim()) && !submitting && !isRunning;
  const whatsappModeLabel = whatsappNumberMode === "existing" ? "Número existente" : "Número novo";

  const stepOneState: StepState = hasConfigured ? "done" : "active";
  const stepTwoState: StepState = isCompleted ? "done" : isRunning || hasConfigured || isFailed ? "active" : "pending";

  const primaryLabel = useMemo(() => {
    if (isRunning) {
      return "Primeira carga em andamento";
    }
    if (isCompleted) {
      return "Salvar ajustes";
    }
    return "Salvar e validar";
  }, [isCompleted, isRunning]);

  const progressTitle = loading
    ? "Preparando seu painel"
    : isCompleted
      ? "Tudo pronto para seguir"
      : isRunning
        ? "Primeira carga em andamento"
        : hasConfigured
          ? "Configuração salva"
          : "Configure o essencial";

  const progressDescription = loading
    ? "Estamos validando sua sessão e carregando os dados iniciais."
    : isCompleted
      ? "A configuração foi salva e a primeira carga já passou."
      : isRunning
        ? "A Alloha está processando a primeira leitura dos imóveis agora."
        : "Preencha o essencial, informe o site e valide a fonte antes da primeira carga.";

  if (loading) {
    return (
      <main className="min-h-screen bg-[#050505] text-white">
        <div className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6">
          <div className="w-full max-w-xl rounded-[28px] border border-white/8 bg-[#090909] p-8 text-center shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03]">
              <LoaderCircle className="h-5 w-5 animate-spin text-[#ff8a4d]" />
            </div>
            <p className="mt-6 text-[11px] uppercase tracking-[0.28em] text-white/42">Onboarding</p>
            <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white">Preparando seu painel</h1>
            <p className="mt-3 text-sm leading-7 text-white/58">Estamos validando sua sessão e organizando o primeiro passo.</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050505] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,122,47,0.12),transparent_24%),linear-gradient(180deg,#050505_0%,#040404_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.018)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.018)_1px,transparent_1px)] bg-[size:40px_40px] opacity-20" />
      </div>

      <div className="relative z-10 grid min-h-screen md:grid-cols-[264px_minmax(0,1fr)]">
        <aside className="hidden border-r border-white/8 bg-black/42 md:flex md:flex-col">
          <div className="px-6 py-6">
            <Link href="/" className="flex min-h-11 items-center gap-3">
              <Image src="/logo.png" alt="Alloha" width={26} height={26} />
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/92">Alloha</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.28em] text-white/38">real estate ai</p>
              </div>
            </Link>
          </div>

          <nav className="px-4">
            <SidebarLink href="/dashboard" label="Onboarding" active />
            <SidebarLink href="/privacy" label="Privacidade" />
            <SidebarLink href="/terms" label="Termos" />
            <SidebarLink href="/contact" label="Contato" />
            <SidebarLink href="/blog" label="Guias" />
          </nav>

          <div className="mt-auto px-4 pb-5 pt-6">
            <div className="rounded-[22px] border border-white/8 bg-white/[0.03] p-4">
              <div className="flex items-center gap-3">
                {profile?.picture ? (
                  <Image
                    src={profile.picture}
                    alt="Avatar"
                    width={42}
                    height={42}
                    className="h-[42px] w-[42px] rounded-full border border-white/12 object-cover"
                    unoptimized
                  />
                ) : (
                  <div className="flex h-[42px] w-[42px] items-center justify-center rounded-full border border-white/12 bg-white/[0.04] text-sm font-semibold text-white">
                    {(profile?.name || "A").slice(0, 1)}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{profile?.name || "Conta conectada"}</p>
                  <p className="truncate text-xs text-white/42">{profile?.email || "Sessão ativa"}</p>
                </div>
              </div>
            </div>
            <button onClick={handleLogout} className="aw-btn-secondary mt-4 w-full justify-center text-sm">
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </aside>

        <section className="min-w-0">
          <header className="border-b border-white/8 bg-black/28 px-5 py-4 backdrop-blur-xl sm:px-8 md:px-10">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 md:hidden">
                <Link href="/" className="flex min-h-11 items-center gap-3">
                  <Image src="/logo.png" alt="Alloha" width={24} height={24} />
                  <span className="text-sm font-semibold uppercase tracking-[0.16em] text-white">Alloha</span>
                </Link>
              </div>

              <div className="hidden md:block">
                <p className="text-sm text-white/42">{profile?.email || "Sessão ativa"}</p>
              </div>

              <div className="flex items-center gap-2">
                <Link href="/contact" className="aw-btn-secondary px-4 py-2 text-sm">
                  Suporte
                </Link>
                <Link href="/privacy" className="hidden min-h-11 items-center px-4 text-sm text-white/58 transition hover:text-white sm:inline-flex">
                  Privacidade
                </Link>
              </div>
            </div>
          </header>

          <div className="mx-auto w-full max-w-4xl px-5 py-10 sm:px-8 md:px-10 md:py-12">
            <div className="max-w-2xl">
              <div className="inline-flex min-h-10 items-center gap-2 rounded-full border border-[#ff8d4d]/18 bg-[#ff5500]/8 px-3 py-2 text-[11px] uppercase tracking-[0.24em] text-[#ffc9a7]">
                <ShieldCheck className="h-4 w-4" />
                Onboarding
              </div>
              <h1 className="mt-6 text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl">Configure sua operação</h1>
              <p className="mt-4 max-w-xl text-base leading-8 text-white/58 sm:text-lg">
                Um fluxo simples para deixar a Alloha pronta para o primeiro uso. Salve os dados básicos, informe o site e veja na hora se a fonte já está pronta para importar os imóveis.
              </p>
            </div>

            <div className="mt-10 rounded-[28px] border border-white/8 bg-[#090909] p-6 shadow-[0_20px_80px_rgba(0,0,0,0.32)] sm:p-8">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.24em] text-white/38">Status atual</p>
                  <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">{progressTitle}</h2>
                  <p className="mt-2 text-sm leading-7 text-white/56">{progressDescription}</p>
                </div>
                <StatusBadge state={isCompleted ? "done" : isRunning ? "active" : "pending"} />
              </div>
            </div>

            <div className="mt-12 space-y-1">
              <StepSection
                step="01"
                title="Complete os dados essenciais"
                description="Preencha o mínimo necessário para configurar a conta e validar de onde os imóveis serão importados."
                state={stepOneState}
              >
                <div className="grid gap-4 md:grid-cols-2">
                  <InputField label="Imobiliária" helper="Nome público da operação.">
                    <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} className="liquid-input" />
                  </InputField>

                  <InputField label="Responsável" helper="Quem está configurando a conta.">
                    <input value={ownerName} onChange={(event) => setOwnerName(event.target.value)} className="liquid-input" />
                  </InputField>

                  <InputField label="Cidade base" helper="Referência inicial da operação.">
                    <input value={city} onChange={(event) => setCity(event.target.value)} className="liquid-input" />
                  </InputField>

                  <InputField label="WhatsApp" helper="Opcional neste primeiro passo.">
                    <input value={whatsappPhone} onChange={(event) => setWhatsappPhone(event.target.value)} placeholder="(opcional)" className="liquid-input" />
                  </InputField>

                  <div className="md:col-span-2">
                    <InputField label="Integração do WhatsApp" helper="Escolha se vamos integrar um número que já existe ou começar com um número novo na Meta.">
                      <div className="grid gap-3 md:grid-cols-2">
                        <button
                          type="button"
                          onClick={() => setWhatsappNumberMode("existing")}
                          className={`rounded-[20px] border px-4 py-4 text-left transition ${
                            whatsappNumberMode === "existing"
                              ? "border-[#ff8b47]/30 bg-[#ff5d16]/10 text-white"
                              : "border-white/8 bg-white/[0.02] text-white/70 hover:border-white/14 hover:text-white"
                          }`}
                        >
                          <span className="block text-sm font-medium">Usar número existente</span>
                          <span className="mt-2 block text-xs leading-6 text-white/46">
                            Indicado quando você já opera esse WhatsApp e quer migrar para a API oficial da Meta.
                          </span>
                        </button>

                        <button
                          type="button"
                          onClick={() => setWhatsappNumberMode("new")}
                          className={`rounded-[20px] border px-4 py-4 text-left transition ${
                            whatsappNumberMode === "new"
                              ? "border-[#ff8b47]/30 bg-[#ff5d16]/10 text-white"
                              : "border-white/8 bg-white/[0.02] text-white/70 hover:border-white/14 hover:text-white"
                          }`}
                        >
                          <span className="block text-sm font-medium">Começar com número novo</span>
                          <span className="mt-2 block text-xs leading-6 text-white/46">
                            Melhor caminho para reduzir risco no MVP e ligar o bot sem mexer no número principal logo de saída.
                          </span>
                        </button>
                      </div>
                    </InputField>
                  </div>

                  <div className="md:col-span-2">
                    <InputField label="Site da imobiliária" helper="Usamos essa URL para validar o portal e decidir se a primeira carga já pode rodar.">
                      <input
                        value={websiteUrl}
                        onChange={(event) => setWebsiteUrl(event.target.value)}
                        placeholder="https://www.seusite.com.br"
                        className="liquid-input"
                      />
                    </InputField>
                  </div>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <button onClick={handleSubmit} disabled={!canSubmit} className="aw-btn-primary min-h-[50px] px-5 text-sm disabled:opacity-60">
                    {submitting ? "Salvando..." : primaryLabel}
                    <ArrowRight className="h-4 w-4" />
                  </button>
                  <p className="text-sm text-white/42">Se o site for compatível com a fonte atual, a primeira carga começa automaticamente.</p>
                </div>

                {message ? (
                  <div className="mt-5 rounded-[20px] border border-[#ffb47c]/16 bg-[#ff7a26]/8 p-4 text-sm leading-7 text-[#ffe7da]">
                    {message}
                  </div>
                ) : null}

                {error ? (
                  <div className="mt-5 rounded-[20px] border border-[#ff9357]/18 bg-[#ff5a1f]/8 p-4 text-sm leading-7 text-[#ffd7c7]">
                    {error}
                  </div>
                ) : null}
              </StepSection>

              <StepSection
                step="02"
                title="Valide a fonte e acompanhe a carga"
                description="Depois do envio, a Alloha inspeciona o site e informa se a importação já pode começar com a estrutura atual."
                state={stepTwoState}
                isLast
              >
                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricTile label="Sessão" value={profile?.email || "Conectada"} />
                  <MetricTile
                    label="Primeira carga"
                    value={isRunning ? "Em execução" : isCompleted ? "Concluída" : isFailed ? "Falhou" : siteReadyForIngest ? "Pronta para iniciar" : "Aguardando validação"}
                    accent={isRunning || isCompleted || isFailed || siteReadyForIngest}
                  />
                  <MetricTile label="WhatsApp" value={whatsappModeLabel} accent />
                </div>

                <div className="mt-5 rounded-[22px] border border-white/8 bg-white/[0.03] p-5 text-sm leading-7 text-white/68">
                  <p>
                    Site:{" "}
                    <strong className="font-semibold text-white">
                      {siteInspection?.final_url || status?.config?.website_url || "Ainda não informado"}
                    </strong>
                  </p>
                  <p>
                    Fonte recomendada:{" "}
                    <strong className="font-semibold text-white">{formatRecommendedSource(siteInspection?.recommended_source)}</strong>
                  </p>
                  <p>
                    Compatibilidade atual:{" "}
                    <strong className="font-semibold text-white">
                      {siteInspection?.ready_for_ingest ? "pronta para importar" : "revisão necessária"}
                    </strong>
                  </p>
                  {siteInspection?.page_title ? <p>Título detectado: {siteInspection.page_title}</p> : null}
                  {siteInspection?.platform_hint ? <p>Plataforma detectada: {siteInspection.platform_hint}</p> : null}
                  {siteInspection?.message ? <p>Leitura: {siteInspection.message}</p> : null}
                </div>

                <div className="mt-5 rounded-[22px] border border-white/8 bg-white/[0.03] p-5 text-sm leading-7 text-white/68">
                  <p>
                    Provedor: <strong className="font-semibold text-white">Meta Cloud API</strong>
                  </p>
                  <p>
                    Caminho escolhido: <strong className="font-semibold text-white">{whatsappModeLabel}</strong>
                  </p>
                  <p>
                    Integração atual:{" "}
                    <strong className="font-semibold text-white">
                      {whatsappSetup?.connected ? "já conectada neste ambiente" : "ainda não conectada"}
                    </strong>
                  </p>
                  <p>
                    Embedded Signup:{" "}
                    <strong className="font-semibold text-white">
                      {whatsappSetup?.embedded_signup_ready ? "pronto para abrir" : "precisa das chaves específicas da Meta"}
                    </strong>
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={handleLaunchMetaSignup}
                      disabled={!whatsappSetup?.embedded_signup_ready || metaBusy}
                      className="aw-btn-primary min-h-[46px] px-4 py-2 text-sm disabled:opacity-60"
                    >
                      {metaBusy ? "Abrindo Meta..." : metaSdkReady ? "Conectar com a Meta" : "Preparar Meta"}
                      {metaBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                    </button>

                    <span className="text-xs text-white/42">
                      {whatsappSetup?.token_exchange_ready
                        ? "A troca automática do código já pode ser concluída no backend."
                        : "Ainda falta o segredo do app para concluir a troca automática do código em token."}
                    </span>
                  </div>
                  {whatsappSetup?.next_step_url ? (
                    <p>
                      Próximo passo: <a className="text-[#ffc39c] underline underline-offset-4" href={whatsappSetup.next_step_url}>abrir fluxo oficial da Meta</a>
                    </p>
                  ) : null}
                  {whatsappSignup ? (
                    <div className="mt-4 rounded-[18px] border border-white/8 bg-black/22 p-4 text-xs leading-6 text-white/58">
                      <p>
                        Último retorno:{" "}
                        <strong className="font-semibold text-white">{formatMetaEvent(whatsappSignup.event)}</strong>
                      </p>
                      <p>Capturado em: {formatTimestamp(whatsappSignup.captured_at)}</p>
                      {whatsappSignup.display_phone_number ? <p>Número retornado: {whatsappSignup.display_phone_number}</p> : null}
                      {whatsappSignup.phone_number_id ? <p>Phone number ID: {whatsappSignup.phone_number_id}</p> : null}
                      {whatsappSignup.waba_id ? <p>WABA ID: {whatsappSignup.waba_id}</p> : null}
                      {whatsappSignup.current_step ? <p>Etapa informada pela Meta: {whatsappSignup.current_step}</p> : null}
                      {whatsappSignup.code_received ? <p>Código temporário recebido pelo frontend e salvo no backend.</p> : null}
                      {whatsappSignup.error_message ? <p>Detalhe: {whatsappSignup.error_message}</p> : null}
                    </div>
                  ) : null}
                </div>

                {status?.last_result ? (
                  <div className="mt-5 rounded-[22px] border border-white/8 bg-white/[0.03] p-5 text-sm leading-7 text-white/68">
                    <p>
                      Resultado: <strong className="font-semibold text-white">{status.last_result.success ? "sucesso" : "falha"}</strong>
                    </p>
                    {typeof status.last_result.total_seen === "number" ? <p>Imóveis encontrados: {status.last_result.total_seen}</p> : null}
                    {typeof status.last_result.inserted_or_updated === "number" ? <p>Imóveis atualizados: {status.last_result.inserted_or_updated}</p> : null}
                    {status.last_result.error ? <p>Erro: {status.last_result.error}</p> : null}
                  </div>
                ) : (
                  <div className="mt-5 rounded-[22px] border border-white/8 bg-white/[0.03] p-5 text-sm leading-7 text-white/58">
                    {siteInspection?.ready_for_ingest
                      ? "O resultado da primeira carga aparece aqui assim que o processo terminar."
                      : "Quando o site estiver compatível com a fonte de importação, a primeira carga aparecerá aqui."}
                  </div>
                )}

                <div className="mt-6 flex flex-wrap gap-3">
                  <Link href="/privacy" className="aw-btn-secondary px-4 py-2 text-sm">
                    Política de privacidade
                  </Link>
                  <Link href="/terms" className="aw-btn-secondary px-4 py-2 text-sm">
                    Termos de uso
                  </Link>
                  <Link href="/contact" className="aw-btn-secondary px-4 py-2 text-sm">
                    Falar com suporte
                  </Link>
                </div>
              </StepSection>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function SidebarLink({ href, label, active = false }: { href: string; label: string; active?: boolean }) {
  return (
    <Link
      href={href}
      className={`mb-1 flex min-h-11 items-center rounded-2xl px-4 text-sm transition ${
        active
          ? "border border-white/10 bg-white/[0.05] text-white"
          : "text-white/54 hover:bg-white/[0.03] hover:text-white"
      }`}
    >
      {label}
    </Link>
  );
}

function StepSection({
  step,
  title,
  description,
  state,
  children,
  isLast = false,
}: {
  step: string;
  title: string;
  description: string;
  state: StepState;
  children: ReactNode;
  isLast?: boolean;
}) {
  return (
    <section className="grid grid-cols-[26px_minmax(0,1fr)] gap-5 sm:gap-6">
      <div className="flex flex-col items-center">
        <StepMarker state={state} />
        {!isLast ? <div className="mt-3 w-px flex-1 bg-white/10" /> : null}
      </div>

      <div className="pb-9">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-[11px] uppercase tracking-[0.22em] text-white/34">Etapa {step}</p>
          <InlineState state={state} />
        </div>
        <h3 className="mt-3 text-[1.8rem] font-semibold tracking-[-0.04em] text-white">{title}</h3>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-white/56">{description}</p>
        <div className="mt-6 rounded-[24px] border border-white/8 bg-[#080808] p-5 sm:p-6">{children}</div>
      </div>
    </section>
  );
}

function StepMarker({ state }: { state: StepState }) {
  if (state === "done") {
    return (
      <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full border border-[#ff8b47]/28 bg-[#ff5d16] text-white shadow-[0_0_0_6px_rgba(255,93,22,0.08)]">
        <Check className="h-4 w-4" />
      </span>
    );
  }

  if (state === "active") {
    return (
      <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full border border-[#ff8b47]/28 bg-white/[0.02] shadow-[0_0_0_6px_rgba(255,93,22,0.05)]">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff8b47]" />
      </span>
    );
  }

  return (
    <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full border border-white/10 bg-transparent text-white/36">
      <CircleDashed className="h-4 w-4" />
    </span>
  );
}

function InlineState({ state }: { state: StepState }) {
  const label = state === "done" ? "Concluído" : state === "active" ? "Em andamento" : "Pendente";
  const className =
    state === "done"
      ? "border-[#ff8a49]/18 bg-[#ff5500]/8 text-[#ffc9a7]"
      : state === "active"
        ? "border-white/10 bg-white/[0.03] text-white/66"
        : "border-white/8 bg-transparent text-white/38";

  return <span className={`rounded-full border px-3 py-1 text-xs ${className}`}>{label}</span>;
}

function StatusBadge({ state }: { state: StepState }) {
  const copy = state === "done" ? "Concluído" : state === "active" ? "Em andamento" : "Pendente";
  const className =
    state === "done"
      ? "border-[#ff8a49]/18 bg-[#ff5500]/8 text-[#ffc9a7]"
      : state === "active"
        ? "border-white/10 bg-white/[0.03] text-white/72"
        : "border-white/8 bg-transparent text-white/42";

  return <div className={`inline-flex min-h-11 items-center rounded-full border px-4 py-2 text-sm ${className}`}>{copy}</div>;
}

function InputField({
  label,
  helper,
  children,
}: {
  label: string;
  helper: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-white/84">{label}</span>
      {children}
      <span className="mt-2 block text-xs leading-6 text-white/42">{helper}</span>
    </label>
  );
}

function MetricTile({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-[18px] border border-white/8 bg-white/[0.02] px-4 py-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-white/34">{label}</p>
      <p className={accent ? "mt-2 text-sm text-[#ffc39c]" : "mt-2 text-sm text-white/72"}>{value}</p>
    </div>
  );
}
