// Auth hook for Arakis authentication

import { useCallback, useEffect } from 'react';
import { useStore } from '@/store';
import { api } from '@/lib/api/client';
import type { AuthProvider } from '@/types';

export function useAuth() {
  const {
    auth,
    setUser,
    setTokens,
    setAuthLoading,
    setAuthError,
    logout: storeLogout,
    initAuth,
  } = useStore();

  // Initialize auth on mount
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  // Fetch user profile when we have tokens but no user
  useEffect(() => {
    const fetchUser = async () => {
      if (auth.accessToken && !auth.user && auth.isLoading) {
        try {
          const user = await api.getCurrentUser();
          setUser(user);
        } catch (error) {
          console.error('Failed to fetch user:', error);
          setAuthError('Failed to load user profile');
          storeLogout();
        }
      }
    };

    fetchUser();
  }, [auth.accessToken, auth.user, auth.isLoading, setUser, setAuthError, storeLogout]);

  // Start OAuth login flow
  const login = useCallback(async (provider: AuthProvider) => {
    setAuthLoading(true);
    setAuthError(null);

    try {
      const currentPath = window.location.pathname;
      let response;

      if (provider === 'google') {
        response = await api.getGoogleLoginUrl(currentPath);
      } else {
        response = await api.getAppleLoginUrl(currentPath);
      }

      // Redirect to OAuth provider
      window.location.href = response.authorization_url;
    } catch (error) {
      console.error('Login failed:', error);
      setAuthError('Failed to start login. Please try again.');
      setAuthLoading(false);
    }
  }, [setAuthLoading, setAuthError]);

  // Handle OAuth callback (called from success page)
  const handleOAuthCallback = useCallback((
    accessToken: string,
    refreshToken: string
  ) => {
    setTokens(accessToken, refreshToken);
    setAuthLoading(true); // Will trigger user fetch
  }, [setTokens, setAuthLoading]);

  // Logout
  const logout = useCallback(async () => {
    try {
      if (auth.refreshToken) {
        await api.logout(auth.refreshToken);
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local logout even if API fails
    }
    storeLogout();
  }, [auth.refreshToken, storeLogout]);

  return {
    user: auth.user,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    error: auth.error,
    login,
    logout,
    handleOAuthCallback,
  };
}
