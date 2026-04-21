"use client";

declare global {
  interface Window {
    FB?: {
      init: (params: Record<string, unknown>) => void;
      login: (
        callback: (response: { authResponse?: { code?: string } } | Record<string, unknown>) => void,
        options: Record<string, unknown>
      ) => void;
    };
    fbAsyncInit?: () => void;
  }
}

let metaSdkPromise: Promise<void> | null = null;

export async function loadMetaEmbeddedSignupSdk(appId: string, version: string) {
  if (typeof window === "undefined") {
    throw new Error("O SDK da Meta só pode ser carregado no navegador.");
  }

  if (!appId) {
    throw new Error("META_APP_ID ausente.");
  }

  if (window.FB) {
    window.FB.init({
      appId,
      autoLogAppEvents: false,
      xfbml: false,
      version,
    });
    return;
  }

  if (!metaSdkPromise) {
    metaSdkPromise = new Promise<void>((resolve, reject) => {
      window.fbAsyncInit = () => {
        if (!window.FB) {
          reject(new Error("O SDK da Meta foi carregado, mas FB não está disponível."));
          return;
        }

        window.FB.init({
          appId,
          autoLogAppEvents: false,
          xfbml: false,
          version,
        });
        resolve();
      };

      const existingScript = document.querySelector<HTMLScriptElement>('script[data-meta-sdk="true"]');
      if (existingScript) {
        return;
      }

      const script = document.createElement("script");
      script.src = "https://connect.facebook.net/pt_BR/sdk.js";
      script.async = true;
      script.defer = true;
      script.dataset.metaSdk = "true";
      script.onerror = () => reject(new Error("Não foi possível carregar o SDK da Meta."));
      document.body.appendChild(script);
    });
  }

  await metaSdkPromise;
}

export function parseMetaEmbeddedSignupMessage(raw: unknown) {
  if (!raw) {
    return null;
  }

  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }

  if (!data || typeof data !== "object") {
    return null;
  }

  const payload = data as Record<string, unknown>;
  if (payload.type !== "WA_EMBEDDED_SIGNUP") {
    return null;
  }

  return payload;
}

export const META_EMBEDDED_SIGNUP_ALLOWED_ORIGINS = [
  "https://www.facebook.com",
  "https://web.facebook.com",
];
