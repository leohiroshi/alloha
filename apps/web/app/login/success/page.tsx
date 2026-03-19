"use client";

import type { ReactNode } from "react";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, LoaderCircle, ShieldAlert, Sparkles } from "lucide-react";
import { ExperienceHero, ExperienceShell, LiquidCard } from "@/components/experience/ExperienceShell";
import api from "@/lib/api";

type Profile = {
  name?: string;
  email?: string;
  picture?: string;
};

function LoginSuccessPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const returnToParam = searchParams.get("return_to") || "/dashboard";
  const returnTo = returnToParam === "/setup" ? "/dashboard" : returnToParam;
  const errorParam = searchParams.get("error");
  const nextLabel = "Ir para o painel";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    const run = async () => {
      if (errorParam) {
        setError(`Falha na autenticação Google: ${errorParam}`);
        setLoading(false);
        return;
      }

      if (!token) {
        setError("Token de sessão ausente.");
        setLoading(false);
        return;
      }

      try {
        localStorage.setItem("alloha_session_token", token);
        const session = await api.getAuthSession(token);
        setProfile(session.profile || null);
        setTimeout(() => router.replace(returnTo), 900);
      } catch (currentError) {
        localStorage.removeItem("alloha_session_token");
        setError(currentError instanceof Error ? currentError.message : "Não foi possível validar a sessão.");
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, [errorParam, returnTo, router, token]);

  const title = loading ? "Estamos conectando sua sessão ao painel." : error ? "O login não conseguiu fechar o ciclo." : "Tudo certo. A sessão está pronta.";
  const description = loading
    ? "O callback do Google já voltou. Agora o backend valida a sessão, grava o estado e segue para o dashboard."
    : error
      ? "O fluxo recebeu um retorno inválido ou incompleto. O caminho seguro é reiniciar a autenticação."
      : "Seu acesso foi confirmado. O redirecionamento acontece automaticamente em instantes.";

  return (
    <ExperienceShell navLinks={[{ href: "/login", label: "Login" }, { href: "/blog", label: "Blog" }, { href: "/contact", label: "Contato" }]}>
      <ExperienceHero
        eyebrow="OAuth Callback"
        title={
          <>
            {title} <span className="text-gradient-sunset">Sem perder o contexto do usuário.</span>
          </>
        }
        description={description}
        actions={
          error ? (
            <Link href="/login" className="aw-btn-primary">
              Tentar novamente
            </Link>
          ) : (
            <Link href={returnTo} className="aw-btn-primary">
              {nextLabel}
            </Link>
          )
        }
        stats={[
          { value: loading ? "validando" : error ? "falhou" : "ok", label: "estado atual da autenticação" },
          { value: "Redis", label: "sessão gravada no backend antes do redirect" },
          { value: "dashboard", label: "destino final do fluxo de entrada" },
        ]}
        aside={
          <div className="space-y-4">
            <div className="glass-chip">Session handshake</div>
            <div className="rounded-[28px] border border-white/10 bg-black/35 p-6">
              <div className="flex items-center gap-3">
                <div className="glass-icon">
                  {loading ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : error ? (
                    <ShieldAlert className="h-4 w-4" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{loading ? "Validando token" : error ? "Callback com falha" : "Sessão confirmada"}</p>
                  <p className="mt-1 text-sm leading-7 text-white/62">
                    {profile?.email ? `Conta conectada: ${profile.email}` : "A resposta final aparece assim que o backend valida a sessão."}
                  </p>
                </div>
              </div>
            </div>

            <div className="glass-list">
              <StateItem title="Receber retorno" body="O navegador volta do Google com código e estado assinados." />
              <StateItem title="Persistir sessão" body="O backend consulta o perfil e salva a sessão antes de devolver o token ao frontend." />
              <StateItem title="Entrar no painel" body="Com tudo validado, o usuário segue para o dashboard sem nova fricção." />
            </div>
          </div>
        }
      />

      <section className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(280px,0.75fr)]">
        <LiquidCard className="p-6 sm:p-8">
          <p className="editorial-kicker">Resultado</p>
          <div className="mt-5 rounded-[28px] border border-white/8 bg-white/[0.03] p-6">
            {loading ? (
              <>
                <div className="flex items-center gap-3 text-white">
                  <LoaderCircle className="h-5 w-5 animate-spin text-[#ffab73]" />
                  <span className="text-lg font-medium">Finalizando login e preparando seu dashboard</span>
                </div>
                <p className="mt-4 text-sm leading-7 text-white/66">
                  A sessão está sendo validada agora. Se estiver tudo certo, o redirecionamento acontece automaticamente.
                </p>
              </>
            ) : error ? (
              <>
                <div className="flex items-center gap-3 text-white">
                  <ShieldAlert className="h-5 w-5 text-[#ff8a5f]" />
                  <span className="text-lg font-medium">Não foi possível concluir o login</span>
                </div>
                <p className="mt-4 text-sm leading-7 text-[#ffd9ca]">{error}</p>
              </>
            ) : (
              <>
                <div className="flex items-center gap-3 text-white">
                  <CheckCircle2 className="h-5 w-5 text-[#ffb074]" />
                  <span className="text-lg font-medium">Login concluído com sucesso</span>
                </div>
                <p className="mt-4 text-sm leading-7 text-white/66">
                  {profile?.name ? `Bem-vindo, ${profile.name}.` : "A autenticação foi concluída e a sessão está pronta para uso."}
                </p>
              </>
            )}
          </div>
        </LiquidCard>

        <LiquidCard className="p-6">
          <p className="editorial-kicker">Próximo passo</p>
          <div className="mt-4 glass-list">
            <StateCard
              icon={loading ? <Sparkles className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
              title="Dashboard"
              body="Painel com atalhos para onboarding, políticas públicas e validação operacional."
            />
            <StateCard
              icon={<ShieldAlert className="h-4 w-4" />}
              title="Fallback"
              body="Se algo falhar, reinicie o fluxo em /login e tente novamente com uma nova sessão."
            />
          </div>
        </LiquidCard>
      </section>
    </ExperienceShell>
  );
}

function StateItem({ title, body }: { title: string; body: string }) {
  return (
    <div className="glass-list-item">
      <div className="glass-icon">{title.slice(0, 1)}</div>
      <div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm leading-7 text-white/62">{body}</p>
      </div>
    </div>
  );
}

function StateCard({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="glass-list-item">
      <div className="glass-icon">{icon}</div>
      <div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm leading-7 text-white/62">{body}</p>
      </div>
    </div>
  );
}

export default function LoginSuccessPage() {
  return (
    <Suspense
      fallback={
        <ExperienceShell>
          <div className="flex min-h-[70vh] items-center justify-center">
            <LiquidCard className="w-full max-w-xl p-8 text-center">
              <p className="editorial-kicker">Callback</p>
              <h1 className="mt-4 text-3xl font-semibold text-white">Recebendo retorno do Google</h1>
            </LiquidCard>
          </div>
        </ExperienceShell>
      }
    >
      <LoginSuccessPageContent />
    </Suspense>
  );
}
