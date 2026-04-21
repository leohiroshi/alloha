const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions extends RequestInit {
  params?: Record<string, string>;
}

interface SiteInspectionPayload {
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
}

interface WhatsAppSetupPayload {
  provider?: string;
  connected?: boolean;
  embedded_signup_ready?: boolean;
  app_id?: string | null;
  embedded_signup_config_id?: string | null;
  token_exchange_ready?: boolean;
  js_sdk_version?: string | null;
  current_phone_number_id?: string | null;
  next_step_url?: string | null;
}

interface WhatsAppSignupPayload {
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
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options;

    let url = `${this.baseUrl}${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...fetchOptions,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      });
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error(`Não foi possível conectar ao backend em ${this.baseUrl}. Verifique se a API local está em execução.`);
      }
      throw error;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  async health() {
    return this.request<{ status: string }>("/health");
  }

  getGoogleAuthStartUrl(returnTo = "/dashboard") {
    const params = new URLSearchParams({ return_to: returnTo });
    return `${this.baseUrl}/v1/auth/google/start?${params.toString()}`;
  }

  async getAuthSession(sessionToken: string) {
    return this.request<{
      authenticated: boolean;
      profile: {
        sub?: string;
        email?: string;
        name?: string;
        picture?: string;
        provider?: string;
      };
    }>("/v1/auth/session", {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    });
  }

  async exchangeSupabaseSession(accessToken: string) {
    return this.request<{
      success: boolean;
      session_token: string;
      profile: {
        sub?: string;
        email?: string;
        name?: string;
        picture?: string;
        provider?: string;
        email_confirmed?: boolean;
      };
    }>("/v1/auth/session/exchange", {
      method: "POST",
      body: JSON.stringify({
        access_token: accessToken,
      }),
    });
  }

  async logout(sessionToken: string) {
    return this.request<{ success: boolean }>("/v1/auth/logout", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    });
  }

  async getOnboardingDefaults(sessionToken: string) {
    return this.request<{
      defaults: {
        business_name: string;
        owner_name: string;
        whatsapp_phone: string;
        whatsapp_number_mode: string;
        city: string;
        website_url: string;
        force_full_scrape: boolean;
        listing_freshness_mode: string;
      };
      whatsapp?: WhatsAppSetupPayload;
      setup_token_required: boolean;
      timestamp: string;
    }>("/v1/onboarding/defaults", {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    });
  }

  async bootstrapOnboarding(
    payload: {
      business_name: string;
      owner_name: string;
      whatsapp_phone: string;
      whatsapp_number_mode: string;
      city: string;
      website_url: string;
      force_full_scrape: boolean;
    },
    sessionToken: string
  ) {
    return this.request<{
      success: boolean;
      setup_id: string;
      started: boolean;
      in_progress: boolean;
      already_configured: boolean;
      message: string;
      site_inspection?: SiteInspectionPayload;
    }>("/v1/onboarding/bootstrap", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify(payload),
    });
  }

  async getOnboardingStatus(sessionToken: string) {
    return this.request<{
      configured: boolean;
      ingest_in_progress: boolean;
      first_scrape_completed: boolean;
      first_scrape_started_at?: string;
      setup_token_required?: boolean;
      whatsapp?: WhatsAppSetupPayload;
      whatsapp_signup?: WhatsAppSignupPayload | null;
      config?: {
        business_name?: string;
        owner_name?: string;
        whatsapp_phone?: string;
        whatsapp_number_mode?: string;
        city?: string;
        website_url?: string;
      };
      site_inspection?: SiteInspectionPayload | null;
      last_result?: {
        success?: boolean;
        message?: string;
        error?: string;
        inserted_or_updated?: number;
        total_seen?: number;
      } | null;
      timestamp: string;
    }>("/v1/onboarding/status", {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    });
  }

  async saveWhatsAppEmbeddedSignup(
    payload: {
      event: string;
      data?: Record<string, unknown>;
      code?: string;
      source?: string;
      raw?: Record<string, unknown>;
    },
    sessionToken: string
  ) {
    return this.request<{
      success: boolean;
      message: string;
      captured: WhatsAppSignupPayload;
    }>("/v1/onboarding/whatsapp/embedded-signup", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify(payload),
    });
  }

  async sendMessage(message: string, sessionId: string, userId = "web-user", channel = "web") {
    return this.request<{
      reply: string;
      session_id: string;
      listings?: Array<{
        property_id: string;
        title: string;
        price: number;
        neighborhood?: string;
      }>;
      capacity_limited?: boolean;
      provider?: string;
      model?: string;
      policy_applied?: string;
    }>("/v1/chat/messages", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        message,
        channel,
      }),
    });
  }

  async createLead(data: {
    name: string;
    phone: string;
    email?: string;
    topic?: string;
    interest?: string;
  }) {
    return this.request<{
      success: boolean;
      lead_id: string;
      created_at?: string;
      message?: string;
      ticket_email?: string;
      notification_delivered?: boolean;
      acknowledgement_sent?: boolean;
    }>("/v1/leads", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getProperties(filters?: {
    q?: string;
    neighborhood?: string;
    min_price?: string;
    max_price?: string;
    bedrooms?: string;
    limit?: string;
  }) {
    return this.request<{
      count: number;
      listings: Array<{
        property_id: string;
        title: string;
        price?: number;
        neighborhood?: string;
        bedrooms?: number;
        main_image?: string;
        url?: string;
      }>;
    }>("/v1/listings/search", { params: filters });
  }
}

export const api = new ApiClient(API_URL);
export default api;
