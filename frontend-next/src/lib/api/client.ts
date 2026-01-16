// API client for Arakis backend

import type {
  WorkflowCreateRequest,
  WorkflowResponse,
  WorkflowListResponse,
  ManuscriptResponse,
  User,
  TokenResponse,
  OAuthLoginResponse,
} from '@/types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public authRequired: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseUrl: string;
  private onTrialLimitReached?: (message: string) => void;
  private onAuthRequired?: () => void;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setOnTrialLimitReached(callback: (message: string) => void) {
    this.onTrialLimitReached = callback;
  }

  setOnAuthRequired(callback: () => void) {
    this.onAuthRequired = callback;
  }

  private getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('arakis-access-token');
  }

  private getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('arakis-refresh-token');
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit & { skipAuth?: boolean }
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options?.headers,
    };

    // Add auth token if available and not skipped
    if (!options?.skipAuth) {
      const token = this.getAccessToken();
      if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - try to refresh token
    if (response.status === 401 && !options?.skipAuth) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        // Retry the request with new token
        return this.request(endpoint, options);
      }
    }

    // Handle 402 Payment Required (trial limit)
    if (response.status === 402) {
      const authRequired = response.headers.get('X-Auth-Required') === 'true';
      const error = await response.json().catch(() => ({}));
      const message = error.detail || 'Trial limit reached. Please sign in to continue.';

      // Trigger login dialog if callback is set
      if (authRequired && this.onTrialLimitReached) {
        this.onTrialLimitReached(message);
      }

      throw new ApiError(response.status, message, authRequired);
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || `Request failed with status ${response.status}`
      );
    }

    // Handle empty responses (204 No Content)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T;
    }

    // Handle different response types
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const text = await response.text();
      if (!text) return undefined as T;
      return JSON.parse(text);
    }
    // For file downloads, return blob
    return response.blob() as unknown as T;
  }

  private async tryRefreshToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        // Refresh failed, clear tokens
        if (typeof window !== 'undefined') {
          localStorage.removeItem('arakis-access-token');
          localStorage.removeItem('arakis-refresh-token');
        }
        this.onAuthRequired?.();
        return false;
      }

      const data: TokenResponse = await response.json();
      if (typeof window !== 'undefined') {
        localStorage.setItem('arakis-access-token', data.access_token);
        localStorage.setItem('arakis-refresh-token', data.refresh_token);
      }
      return true;
    } catch {
      return false;
    }
  }

  // ============= Auth Endpoints =============

  async getGoogleLoginUrl(redirectUrl?: string): Promise<OAuthLoginResponse> {
    const params = redirectUrl ? `?redirect_url=${encodeURIComponent(redirectUrl)}` : '';
    return this.request(`/api/auth/google/login${params}`, { skipAuth: true });
  }

  async getAppleLoginUrl(redirectUrl?: string): Promise<OAuthLoginResponse> {
    const params = redirectUrl ? `?redirect_url=${encodeURIComponent(redirectUrl)}` : '';
    return this.request(`/api/auth/apple/login${params}`, { skipAuth: true });
  }

  async refreshTokens(refreshToken: string): Promise<TokenResponse> {
    return this.request('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuth: true,
    });
  }

  async logout(refreshToken: string): Promise<void> {
    return this.request('/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getCurrentUser(): Promise<User> {
    return this.request('/api/auth/me');
  }

  // ============= Workflow Endpoints =============

  async createWorkflow(data: WorkflowCreateRequest): Promise<WorkflowResponse> {
    return this.request('/api/workflows/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWorkflow(id: string): Promise<WorkflowResponse> {
    return this.request(`/api/workflows/${id}`);
  }

  async listWorkflows(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<WorkflowListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.status) searchParams.set('status', params.status);

    const query = searchParams.toString();
    return this.request(`/api/workflows/${query ? `?${query}` : ''}`);
  }

  async deleteWorkflow(id: string): Promise<void> {
    return this.request(`/api/workflows/${id}`, { method: 'DELETE' });
  }

  // ============= Manuscript Endpoints =============

  async getManuscript(workflowId: string): Promise<ManuscriptResponse> {
    return this.request(`/api/manuscripts/${workflowId}/json`);
  }

  async exportMarkdown(workflowId: string): Promise<Blob> {
    return this.request(`/api/manuscripts/${workflowId}/markdown`);
  }

  async exportPdf(workflowId: string): Promise<Blob> {
    return this.request(`/api/manuscripts/${workflowId}/pdf`);
  }

  async exportDocx(workflowId: string): Promise<Blob> {
    return this.request(`/api/manuscripts/${workflowId}/docx`);
  }

  // ============= Health Check =============

  async healthCheck(): Promise<{ status: string; database: string }> {
    return this.request('/health');
  }
}

// Singleton instance
export const api = new ApiClient(API_BASE_URL);

// Helper function to download blob as file
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
