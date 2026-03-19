"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import type { EmailOtpType } from "@supabase/supabase-js";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { exchangeSupabaseAccessToken } from "@/lib/auth-session";
import { getSupabaseBrowserClient } from "@/lib/supabase";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") || "/dashboard";
  const queryError = searchParams.get("error_description") || searchParams.get("error");
  const tokenHash = searchParams.get("token_hash");
  const tokenType = searchParams.get("type");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("Finalizando sua autenticação...");
  const handledRef = useRef(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let unsubscribe: (() => void) | null = null;
    let cancelled = false;

    const finish = async (accessToken: string) => {
      if (handledRef.current || cancelled) {
        return;
      }
      handledRef.current = true;

      try {
        await exchangeSupabaseAccessToken(accessToken);
        if (cancelled) {
          return;
        }
        setMessage("Sessão confirmada. Redirecionando...");
        router.replace(nextPath);
      } catch (currentError) {
        if (!cancelled) {
          setError(currentError instanceof Error ? currentError.message : "Não foi possível concluir a autenticação.");
        }
      }
    };

    const run = async () => {
      if (queryError) {
        setError(`Falha na autenticação: ${queryError}`);
        return;
      }

      try {
        const supabase = getSupabaseBrowserClient();
        const supportedTokenTypes: EmailOtpType[] = ["email", "invite", "recovery", "email_change"];

        if (tokenHash && tokenType && supportedTokenTypes.includes(tokenType as EmailOtpType)) {
          setMessage(tokenType === "email" ? "Confirmando seu e-mail..." : "Confirmando acesso...");
          const { data: verifyData, error: verifyError } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: tokenType as EmailOtpType,
          });

          if (verifyError) {
            throw verifyError;
          }

          if (verifyData.session?.access_token) {
            await finish(verifyData.session.access_token);
            return;
          }
        }

        const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
          if (session?.access_token) {
            void finish(session.access_token);
          }
        });
        unsubscribe = () => {
          listener.subscription.unsubscribe();
        };

        const { data } = await supabase.auth.getSession();
        if (data.session?.access_token) {
          await finish(data.session.access_token);
          return;
        }

        timeoutId = setTimeout(async () => {
          const latest = await supabase.auth.getSession();
          if (latest.data.session?.access_token) {
            await finish(latest.data.session.access_token);
            return;
          }
          if (!cancelled) {
            setError("Não encontramos uma sessão válida no retorno do Supabase.");
          }
        }, 1400);
      } catch (currentError) {
        if (!cancelled) {
          setError(currentError instanceof Error ? currentError.message : "Não foi possível concluir a autenticação.");
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
  }, [nextPath, queryError, router, tokenHash, tokenType]);

  return (
    <main className="flex h-dvh items-center justify-center overflow-hidden bg-[#050505] px-5 text-white">
      <div className="w-full max-w-[440px] rounded-[30px] border border-white/8 bg-black/48 px-6 py-7 text-center shadow-[0_30px_120px_rgba(0,0,0,0.58)] backdrop-blur-2xl sm:px-8 sm:py-8">
        <div className="mx-auto flex h-[68px] w-[68px] items-center justify-center rounded-[22px] border border-white/8 bg-white/[0.03]">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-[16px] border border-[#ff7a2f]/16 bg-black/85">
            <Image src="/logo.png" alt="Alloha" width={26} height={26} />
          </div>
        </div>

        <div className="mt-6 flex justify-center">
          <LoaderCircle className="h-6 w-6 animate-spin text-[#ff9e6b]" />
        </div>

        <h1 className="mt-5 text-[2rem] font-semibold tracking-[-0.04em] text-white">Confirmando acesso</h1>
        <p className="mt-3 text-[15px] leading-7 text-white/50">{message}</p>

        {error ? (
          <div className="mt-5 rounded-[18px] border border-[#ff7a2f]/22 bg-[#ff5a1f]/8 px-4 py-3 text-sm leading-6 text-[#ffd8c7]">
            {error}
          </div>
        ) : null}

        <div className="mt-6 text-sm text-white/42">
          <Link href="/login" className="text-white/72 underline decoration-white/20 underline-offset-4 transition hover:text-white">
            Voltar para login
          </Link>
        </div>
      </div>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<AuthCallbackFallback />}>
      <AuthCallbackContent />
    </Suspense>
  );
}

function AuthCallbackFallback() {
  return (
    <main className="flex h-dvh items-center justify-center overflow-hidden bg-[#050505] px-5 text-white">
      <div className="w-full max-w-[440px] rounded-[30px] border border-white/8 bg-black/48 px-6 py-7 text-center shadow-[0_30px_120px_rgba(0,0,0,0.58)] backdrop-blur-2xl sm:px-8 sm:py-8">
        <div className="mx-auto flex h-[68px] w-[68px] items-center justify-center rounded-[22px] border border-white/8 bg-white/[0.03]">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-[16px] border border-[#ff7a2f]/16 bg-black/85">
            <Image src="/logo.png" alt="Alloha" width={26} height={26} />
          </div>
        </div>
        <h1 className="mt-6 text-[2rem] font-semibold tracking-[-0.04em] text-white">Preparando autenticação</h1>
      </div>
    </main>
  );
}
