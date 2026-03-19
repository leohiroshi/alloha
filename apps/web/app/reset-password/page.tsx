"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import type { EmailOtpType } from "@supabase/supabase-js";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import { AuthMessage } from "@/components/auth/AuthMessage";
import { clearAllohaAuth } from "@/lib/auth-session";
import { getSupabaseBrowserClient } from "@/lib/supabase";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tokenHash = searchParams.get("token_hash");
  const tokenType = searchParams.get("type");
  const [password, setPassword] = useState("");
  const [ready, setReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const handledRef = useRef(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let unsubscribe: (() => void) | null = null;
    let cancelled = false;

    const allowReset = () => {
      if (cancelled || handledRef.current) {
        return;
      }
      handledRef.current = true;
      setReady(true);
    };

    const queryError = searchParams.get("error_description") || searchParams.get("error");
    if (queryError) {
      setError(`Falha na recuperação: ${queryError}`);
      return () => undefined;
    }

    const run = async () => {
      try {
        const supabase = getSupabaseBrowserClient();
        const supportedTokenTypes: EmailOtpType[] = ["recovery", "email_change"];

        if (tokenHash && tokenType && supportedTokenTypes.includes(tokenType as EmailOtpType)) {
          const { data: verifyData, error: verifyError } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: tokenType as EmailOtpType,
          });

          if (verifyError) {
            throw verifyError;
          }

          if (verifyData.session?.access_token) {
            allowReset();
            return;
          }
        }

        const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
          if ((event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") && session?.access_token) {
            allowReset();
          }
        });
        unsubscribe = () => {
          listener.subscription.unsubscribe();
        };

        const { data } = await supabase.auth.getSession();
        if (data.session?.access_token) {
          allowReset();
          return;
        }

        timeoutId = setTimeout(async () => {
          const latest = await supabase.auth.getSession();
          if (latest.data.session?.access_token) {
            allowReset();
            return;
          }

          if (!cancelled) {
            setError("Esse link de recuperação é inválido ou expirou. Solicite um novo e-mail.");
          }
        }, 1400);
      } catch (currentError) {
        if (!cancelled) {
          setError(currentError instanceof Error ? currentError.message : "Não foi possível abrir a recuperação de senha.");
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
      unsubscribe?.();
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [searchParams, tokenHash, tokenType]);

  const friendlyError = (message: string) => {
    const normalized = message.toLowerCase();
    if (normalized.includes("same password")) {
      return "Escolha uma senha diferente da atual.";
    }
    if (normalized.includes("weak password") || normalized.includes("password should")) {
      return "Use uma senha com pelo menos 8 caracteres.";
    }
    return message;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      if (password.length < 8) {
        throw new Error("Use uma senha com pelo menos 8 caracteres.");
      }

      const supabase = getSupabaseBrowserClient();
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });

      if (updateError) {
        throw updateError;
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();

      const nextEmail = session?.user?.email ? `&email=${encodeURIComponent(session.user.email)}` : "";
      await clearAllohaAuth();
      setNotice("Senha atualizada. Voltando para login...");
      router.replace(`/login?notice=password-reset${nextEmail}`);
    } catch (currentError) {
      setError(friendlyError(currentError instanceof Error ? currentError.message : "Não foi possível atualizar sua senha."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="relative h-dvh overflow-hidden bg-[#050505] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_18%,rgba(255,255,255,0.05),transparent_24%),radial-gradient(circle_at_80%_12%,rgba(255,255,255,0.04),transparent_24%),linear-gradient(180deg,#080808_0%,#040404_100%)]" />
        <div className="absolute -left-[22vw] bottom-[-26vh] h-[68vh] w-[48vw] rotate-[-32deg] rounded-[42%] bg-[linear-gradient(180deg,rgba(255,255,255,0.18),rgba(255,255,255,0.03))] opacity-70 blur-[10px]" />
        <div className="absolute -right-[12vw] -top-[14vh] h-[72vh] w-[40vw] rotate-[26deg] rounded-[44%] bg-[linear-gradient(180deg,rgba(255,255,255,0.18),rgba(255,255,255,0.03))] opacity-70 blur-[12px]" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-[radial-gradient(circle_at_50%_100%,rgba(255,85,0,0.12),transparent_55%)]" />
      </div>

      <div className="relative z-10 flex h-full flex-col px-5 py-5 sm:px-8 sm:py-8">
        <div className="flex min-h-11 items-center justify-between">
          <Link href="/login" className="inline-flex min-h-11 items-center gap-2 text-sm text-white/58 transition hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Voltar para login
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-[460px] rounded-[30px] border border-white/8 bg-black/48 px-6 py-6 shadow-[0_30px_120px_rgba(0,0,0,0.58)] backdrop-blur-2xl sm:px-8 sm:py-7">
            <div className="mx-auto flex h-[68px] w-[68px] items-center justify-center rounded-[22px] border border-white/8 bg-white/[0.03] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
              <div className="relative flex h-11 w-11 items-center justify-center rounded-[16px] border border-[#ff7a2f]/16 bg-black/85">
                <Image src="/logo.png" alt="Alloha" width={26} height={26} />
              </div>
            </div>

            <div className="mt-5 text-center">
              <h1 className="text-[2rem] font-semibold tracking-[-0.04em] text-white">Definir nova senha</h1>
              <p className="mt-2 text-[15px] text-white/46">Escolha uma nova senha para voltar direto ao painel.</p>
            </div>

            {!ready && !error ? (
              <div className="mt-6 rounded-[18px] border border-white/8 bg-white/[0.02] px-4 py-5 text-center text-sm leading-6 text-white/56">
                <div className="mb-3 flex justify-center">
                  <LoaderCircle className="h-5 w-5 animate-spin text-[#ff9e6b]" />
                </div>
                Validando seu link de recuperação...
              </div>
            ) : null}

            {ready ? (
              <form onSubmit={handleSubmit} className="mt-6 space-y-3">
                <div>
                  <label htmlFor="new-password" className="mb-2 block text-sm text-white/62">
                    Nova senha
                  </label>
                  <input
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Mínimo de 8 caracteres"
                    className="liquid-input h-[50px] rounded-[18px]"
                  />
                </div>

                <button type="submit" disabled={submitting} className="aw-btn-primary mt-1 min-h-[54px] w-full rounded-[18px] text-[15px] disabled:opacity-60">
                  {submitting ? "Atualizando..." : "Salvar nova senha"}
                </button>
              </form>
            ) : null}

            <div className="mt-4 rounded-[18px] border border-white/8 bg-white/[0.02] px-4 py-3 text-sm leading-6 text-white/52">
              Esse fluxo usa a sessão temporária do Supabase para validar o link e concluir a troca da senha com segurança.
            </div>

            {notice ? (
              <div className="mt-4">
                <AuthMessage title="Tudo certo" body={notice} variant="success" />
              </div>
            ) : null}

            {error ? (
              <div role="alert" className="mt-4">
                <AuthMessage title="Não foi possível concluir" body={error} variant="error" />
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<ResetPasswordFallback />}>
      <ResetPasswordContent />
    </Suspense>
  );
}

function ResetPasswordFallback() {
  return (
    <main className="flex h-dvh items-center justify-center overflow-hidden bg-[#050505] px-5 text-white">
      <div className="w-full max-w-[460px] rounded-[30px] border border-white/8 bg-black/48 px-6 py-7 text-center shadow-[0_30px_120px_rgba(0,0,0,0.58)] backdrop-blur-2xl sm:px-8 sm:py-8">
        <div className="mx-auto flex h-[68px] w-[68px] items-center justify-center rounded-[22px] border border-white/8 bg-white/[0.03]">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-[16px] border border-[#ff7a2f]/16 bg-black/85">
            <Image src="/logo.png" alt="Alloha" width={26} height={26} />
          </div>
        </div>
        <h1 className="mt-6 text-[2rem] font-semibold tracking-[-0.04em] text-white">Preparando redefinição</h1>
      </div>
    </main>
  );
}
