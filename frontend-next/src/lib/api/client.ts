// API client for Arakis backend

import type {
  WorkflowCreateRequest,
  WorkflowResponse,
  WorkflowListResponse,
  ManuscriptResponse,
} from '@/types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

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
