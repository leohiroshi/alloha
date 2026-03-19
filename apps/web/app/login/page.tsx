"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import { AuthMessage } from "@/components/auth/AuthMessage";
import { exchangeSupabaseAccessToken, resolveAuthenticatedSession } from "@/lib/auth-session";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type AuthMode = "login" | "signup" | "recovery";
type PendingAction = "google" | "credentials" | "recovery" | null;
type NoticeState = {
  title: string;
  body: string;
};

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawMode = searchParams.get("mode");
  const mode: AuthMode = rawMode === "signup" ? "signup" : rawMode === "recovery" ? "recovery" : "login";
  const nextPath = "/dashboard";

  const [checkingSession, setCheckingSession] = useState(true);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);

  useEffect(() => {
    const prefilledEmail = searchParams.get("email");
    if (prefilledEmail) {
      setEmail(prefilledEmail);
    }

    const noticeState = searchParams.get("notice");
    if (noticeState === "password-reset") {
      setNotice({
        title: "Senha redefinida",
        body: "Entre com sua nova senha para continuar.",
      });
      setError(null);
      return;
    }

    if (!noticeState) {
      setNotice(null);
    }
  }, [searchParams]);

  useEffect(() => {
    const syncExistingSession = async () => {
      const resolved = await resolveAuthenticatedSession();
      if (resolved) {
        router.replace("/dashboard");
        return;
      }
      setCheckingSession(false);
    };

    void syncExistingSession();
  }, [router]);

  const switchCopy = useMemo(() => {
    if (mode === "signup") {
      return {
        title: "Criar sua conta",
        subtitle: "Já tem conta?",
        href: "/login",
        label: "Entrar",
        primary: "Criar conta",
        helper: "Crie sua conta e confirme seu e-mail para começar.",
      };
    }

    if (mode === "recovery") {
      return {
        title: "Recuperar acesso",
        subtitle: "Lembrou a senha?",
        href: "/login",
        label: "Voltar para entrar",
        primary: "Enviar link",
        helper: "Enviaremos um link seguro para você criar uma nova senha.",
      };
    }

    return {
      title: "Entrar na Alloha",
      subtitle: "Não tem conta?",
      href: "/login?mode=signup",
      label: "Cadastrar-se",
      primary: "Entrar",
      helper: "Acesse seu painel e continue a configuração.",
    };
  }, [mode]);

  const friendlyError = (message: string) => {
    const normalized = message.toLowerCase();
    if (normalized.includes("invalid login credentials")) {
      return "E-mail ou senha inválidos.";
    }
    if (normalized.includes("email not confirmed") || normalized.includes("email validation pending")) {
      return "Seu e-mail ainda não foi confirmado. Abra o link que enviamos e tente novamente.";
    }
    if (normalized.includes("user already registered")) {
      return "Esse e-mail já possui conta. Entre ou recupere a senha.";
    }
    if (normalized.includes("error sending confirmation email")) {
      return "Não foi possível enviar o e-mail de confirmação. Revise a configuração de e-mail do Supabase e tente novamente.";
    }
    if (normalized.includes("email address not authorized")) {
      return "O provedor de e-mail recusou o envio. Revise o remetente e as credenciais SMTP configuradas no Supabase.";
    }
    if (normalized.includes("for security purposes")) {
      return "Se esse e-mail existir, o link de recuperação será enviado em instantes.";
    }
    if (normalized.includes("supabase auth is not configured")) {
      return "A autenticação do Supabase ainda não foi configurada neste ambiente.";
    }
    return message;
  };

  const handleGoogleLogin = async () => {
    setPendingAction("google");
    setError(null);
    setNotice(null);

    try {
      const supabase = getSupabaseBrowserClient();
      const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`;
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
          queryParams: {
            access_type: "offline",
            prompt: "select_account",
          },
        },
      });

      if (oauthError) {
        throw oauthError;
      }
    } catch (currentError) {
      setPendingAction(null);
      setError(friendlyError(currentError instanceof Error ? currentError.message : "Não foi possível iniciar o login com Google."));
    }
  };

  const handleFormSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPendingAction(mode === "recovery" ? "recovery" : "credentials");
    setError(null);
    setNotice(null);

    try {
      const supabase = getSupabaseBrowserClient();

      if (!email.trim()) {
        throw new Error("Informe seu e-mail.");
      }

      if (mode === "recovery") {
        const redirectTo = `${window.location.origin}/reset-password`;
        const { error: recoveryError } = await supabase.auth.resetPasswordForEmail(email.trim(), {
          redirectTo,
        });

        if (recoveryError) {
          throw recoveryError;
        }

        setNotice({
          title: "Link enviado",
          body: "Se esse e-mail existir, enviaremos as instruções para redefinir sua senha.",
        });
        return;
      }

      if (password.length < 8) {
        throw new Error("A senha precisa ter pelo menos 8 caracteres.");
      }

      if (mode === "signup") {
        const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent("/dashboard")}`;
        const { data, error: signUpError } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            emailRedirectTo: redirectTo,
          },
        });

        if (signUpError) {
          throw signUpError;
        }

        if (data.session?.access_token) {
          await exchangeSupabaseAccessToken(data.session.access_token);
          router.replace("/dashboard");
          return;
        }

        setNotice({
          title: "Verifique seu e-mail",
          body: "Enviamos um link de confirmação. Depois disso, é só entrar e continuar.",
        });
        setPassword("");
        return;
      }

      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (signInError) {
        throw signInError;
      }
      if (!data.session?.access_token) {
        throw new Error("Sessão de autenticação ausente.");
      }

      await exchangeSupabaseAccessToken(data.session.access_token);
      router.replace(nextPath);
    } catch (currentError) {
      setError(
        friendlyError(
          currentError instanceof Error
            ? currentError.message
            : mode === "recovery"
              ? "Não foi possível enviar o link de recuperação."
              : "Não foi possível autenticar sua conta."
        )
      );
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <main className="relative min-h-dvh overflow-y-auto bg-[#050505] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_20%,rgba(255,255,255,0.06),transparent_24%),radial-gradient(circle_at_82%_16%,rgba(255,255,255,0.045),transparent_24%),linear-gradient(180deg,#080808_0%,#040404_100%)]" />
        <div className="absolute -left-[22vw] bottom-[-26vh] h-[68vh] w-[48vw] rotate-[-32deg] rounded-[42%] bg-[linear-gradient(180deg,rgba(255,255,255,0.18),rgba(255,255,255,0.03))] opacity-70 blur-[10px]" />
        <div className="absolute -right-[12vw] -top-[14vh] h-[72vh] w-[40vw] rotate-[26deg] rounded-[44%] bg-[linear-gradient(180deg,rgba(255,255,255,0.18),rgba(255,255,255,0.03))] opacity-70 blur-[12px]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:56px_56px] opacity-15" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-[radial-gradient(circle_at_50%_100%,rgba(255,85,0,0.12),transparent_55%)]" />
      </div>

      <div className="relative z-10 min-h-dvh px-5 py-5 sm:px-8 sm:py-8">
        <div className="flex min-h-11 items-center justify-between">
          <Link href="/" className="inline-flex min-h-11 items-center gap-2 text-sm text-white/58 transition hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Início
          </Link>
        </div>

        <div className="flex min-h-[calc(100dvh-72px)] items-center justify-center py-6 sm:py-10">
          <div className="w-full max-w-[430px] rounded-[28px] border border-white/8 bg-black/48 px-5 py-5 shadow-[0_24px_90px_rgba(0,0,0,0.56)] backdrop-blur-2xl sm:px-7 sm:py-6">
            <div className="mx-auto flex h-[60px] w-[60px] items-center justify-center rounded-[20px] border border-white/8 bg-white/[0.03] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-[14px] border border-[#ff7a2f]/16 bg-black/85">
                <Image src="/logo.png" alt="Alloha" width={26} height={26} />
              </div>
            </div>

            <div className="mt-4 text-center">
              <h1 className="text-[1.9rem] font-semibold tracking-[-0.04em] text-white">{switchCopy.title}</h1>
              <p className="mt-2 text-[14px] text-white/46">
                {switchCopy.subtitle}{" "}
                <Link href={switchCopy.href} className="font-semibold text-white transition hover:text-[#ffb280]">
                  {switchCopy.label}
                </Link>
              </p>
              <p className="mt-2 text-sm text-white/38">{switchCopy.helper}</p>
            </div>

            <div className="mt-4 space-y-3">
              {mode !== "recovery" ? (
                <>
                  <button
                    type="button"
                    onClick={handleGoogleLogin}
                    disabled={checkingSession || pendingAction !== null}
                    className="inline-flex min-h-[54px] w-full items-center justify-center gap-3 rounded-[18px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.1),rgba(255,255,255,0.04))] px-5 text-[15px] font-semibold text-white shadow-[0_18px_50px_rgba(0,0,0,0.32)] transition hover:border-[#ff7a2f]/28 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.05))] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {checkingSession || pendingAction === "google" ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <GoogleMark />}
                    <span>{checkingSession ? "Verificando sessão..." : "Entrar com Google"}</span>
                  </button>

                  <div className="flex items-center gap-4 text-xs text-white/28">
                    <div className="h-px flex-1 bg-white/8" />
                    <span>ou</span>
                    <div className="h-px flex-1 bg-white/8" />
                  </div>
                </>
              ) : null}

              <form onSubmit={handleFormSubmit} className="space-y-3">
                <div>
                  <label htmlFor="email" className="mb-2 block text-sm text-white/62">
                    E-mail
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="você@empresa.com"
                    className="liquid-input h-[50px] rounded-[18px]"
                  />
                </div>

                {mode !== "recovery" ? (
                  <div>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <label htmlFor="password" className="block text-sm text-white/62">
                        Senha
                      </label>
                      {mode === "login" ? (
                        <Link href="/login?mode=recovery" className="text-xs font-medium text-white/54 transition hover:text-[#ffb280]">
                          Esqueci minha senha
                        </Link>
                      ) : null}
                    </div>
                    <input
                      id="password"
                      type="password"
                      autoComplete={mode === "signup" ? "new-password" : "current-password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Mínimo de 8 caracteres"
                      className="liquid-input h-[50px] rounded-[18px]"
                    />
                  </div>
                ) : null}

                <button
                  type="submit"
                  disabled={checkingSession || pendingAction !== null}
                  className="aw-btn-primary mt-1 min-h-[54px] w-full rounded-[18px] text-[15px] disabled:opacity-60"
                >
                  {pendingAction === "credentials"
                    ? "Processando..."
                    : pendingAction === "recovery"
                      ? "Enviando..."
                      : switchCopy.primary}
                </button>
              </form>

              {mode === "login" ? (
                <p className="text-center text-xs leading-6 text-white/38">
                  Prefere redefinir por e-mail?{" "}
                  <Link href="/login?mode=recovery" className="text-white/62 underline decoration-white/15 underline-offset-4 transition hover:text-white">
                    Enviar link de recuperação
                  </Link>
                </p>
              ) : null}
            </div>

            {notice ? (
              <div className="mt-4">
                <AuthMessage title={notice.title} body={notice.body} variant="success" />
              </div>
            ) : null}

            {error ? (
              <div role="alert" className="mt-4">
                <AuthMessage title="Não foi possível concluir" body={error} variant="error" />
              </div>
            ) : null}

            {mode === "signup" ? (
              <p className="mt-4 text-center text-xs leading-6 text-white/40">
                Ao criar sua conta, você aceita nossos{" "}
                <Link href="/terms" className="text-white/72 underline decoration-white/20 underline-offset-4 transition hover:text-white">
                  Termos de Uso
                </Link>{" "}
                e{" "}
                <Link href="/privacy" className="text-white/72 underline decoration-white/20 underline-offset-4 transition hover:text-white">
                  Política de Privacidade
                </Link>
                .
              </p>
            ) : null}

            {mode === "recovery" ? (
              <p className="mt-5 text-center text-sm leading-6 text-white/40">
                O link abre em uma página segura da Alloha para você definir uma nova senha.
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 text-white">
      <path fill="currentColor" d="M21.81 10.04H12.2v3.92h5.52c-.24 1.26-.96 2.33-2.04 3.05v2.53h3.3c1.93-1.78 3.05-4.4 3.05-7.52 0-.67-.06-1.33-.22-1.98Z" />
      <path fill="currentColor" d="M12.2 22c2.76 0 5.07-.91 6.76-2.46l-3.3-2.53c-.92.62-2.09.99-3.46.99-2.66 0-4.91-1.79-5.72-4.2H3.08v2.61A10.2 10.2 0 0 0 12.2 22Z" />
      <path fill="currentColor" d="M6.48 13.8A6.11 6.11 0 0 1 6.16 12c0-.62.12-1.21.32-1.8V7.59H3.08A10.17 10.17 0 0 0 2 12c0 1.64.39 3.19 1.08 4.41l3.4-2.61Z" />
      <path fill="currentColor" d="M12.2 6.05c1.5 0 2.84.52 3.9 1.52l2.92-2.92C17.26 2.99 14.95 2 12.2 2A10.2 10.2 0 0 0 3.08 7.59l3.4 2.61c.8-2.41 3.06-4.15 5.72-4.15Z" />
    </svg>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginFallback() {
  return (
    <main className="min-h-dvh overflow-y-auto bg-[#050505] px-5 py-8 text-white">
      <div className="mx-auto flex min-h-[calc(100dvh-64px)] w-full max-w-[430px] items-center">
        <div className="w-full rounded-[28px] border border-white/8 bg-black/48 px-5 py-6 text-center shadow-[0_24px_90px_rgba(0,0,0,0.56)] backdrop-blur-2xl sm:px-7">
          <div className="mx-auto flex h-[60px] w-[60px] items-center justify-center rounded-[20px] border border-white/8 bg-white/[0.03]">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-[14px] border border-[#ff7a2f]/16 bg-black/85">
              <Image src="/logo.png" alt="Alloha" width={26} height={26} />
            </div>
          </div>
          <h1 className="mt-5 text-[1.9rem] font-semibold tracking-[-0.04em] text-white">Preparando acesso</h1>
          <p className="mt-2 text-[14px] text-white/46">Carregando a autenticação da Alloha.</p>
        </div>
      </div>
    </main>
  );
}
