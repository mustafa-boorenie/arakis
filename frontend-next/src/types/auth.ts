// Authentication types for Arakis frontend

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  phone_number: string | null;
  affiliation: string | null;
  avatar_url: string | null;
  auth_provider: 'google' | 'apple' | 'email';
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  total_workflows: number;
  total_cost: number;
}

export interface UpdateUserRequest {
  full_name?: string;
  phone_number?: string;
  affiliation?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface OAuthLoginResponse {
  authorization_url: string;
  state: string;
}

export type AuthProvider = 'google' | 'apple';

// Token storage keys
export const AUTH_STORAGE_KEY = 'arakis-auth';
export const ACCESS_TOKEN_KEY = 'arakis-access-token';
export const REFRESH_TOKEN_KEY = 'arakis-refresh-token';
