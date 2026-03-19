import api from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export const APP_SESSION_STORAGE_KEY = "alloha_session_token";

type AppProfile = {
  sub?: string;
  email?: string;
  name?: string;
  picture?: string;
  provider?: string;
  email_confirmed?: boolean;
};

export async function exchangeSupabaseAccessToken(accessToken: string) {
  const response = await api.exchangeSupabaseSession(accessToken);
  localStorage.setItem(APP_SESSION_STORAGE_KEY, response.session_token);
  return response;
}

export async function resolveAuthenticatedSession(): Promise<{ token: string; profile: AppProfile } | null> {
  const storedToken = localStorage.getItem(APP_SESSION_STORAGE_KEY);
  if (storedToken) {
    try {
      const session = await api.getAuthSession(storedToken);
      return { token: storedToken, profile: session.profile || {} };
    } catch {
      localStorage.removeItem(APP_SESSION_STORAGE_KEY);
    }
  }

  try {
    const supabase = getSupabaseBrowserClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      return null;
    }

    const exchanged = await exchangeSupabaseAccessToken(session.access_token);
    return { token: exchanged.session_token, profile: exchanged.profile || {} };
  } catch {
    return null;
  }
}

export async function clearAllohaAuth() {
  const storedToken = localStorage.getItem(APP_SESSION_STORAGE_KEY);
  if (storedToken) {
    try {
      await api.logout(storedToken);
    } catch {
      // Keep logout resilient.
    }
  }

  localStorage.removeItem(APP_SESSION_STORAGE_KEY);

  try {
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.signOut();
  } catch {
    // Ignore sign out errors to avoid trapping the user.
  }
}
