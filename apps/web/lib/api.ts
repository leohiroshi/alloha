const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiOptions extends RequestInit {
  params?: Record<string, string>;
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

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async health() {
    return this.request<{ status: string }>('/health');
  }

  // Chat endpoint
  async sendMessage(message: string, sessionId: string) {
    return this.request<{
      response: string;
      session_id: string;
      properties?: Array<{
        id: string;
        title: string;
        price: number;
        location: string;
      }>;
    }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    });
  }

  // Leads
  async createLead(data: {
    name: string;
    phone: string;
    email?: string;
    interest?: string;
  }) {
    return this.request<{ id: string; created_at: string }>('/leads', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Properties
  async getProperties(filters?: {
    location?: string;
    min_price?: string;
    max_price?: string;
    bedrooms?: string;
  }) {
    return this.request<Array<{
      id: string;
      title: string;
      price: number;
      location: string;
      bedrooms: number;
      image_url?: string;
    }>>('/properties', { params: filters });
  }

  // Webhook simulation (for testing)
  async simulateWhatsAppWebhook(phone: string, message: string) {
    return this.request('/webhooks/whatsapp/simulate', {
      method: 'POST',
      body: JSON.stringify({ phone, message }),
    });
  }
}

export const api = new ApiClient(API_URL);
export default api;
