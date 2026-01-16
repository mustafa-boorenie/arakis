'use client';

import { useEffect } from 'react';
import { useStore } from '@/store';
import { useAuth } from '@/hooks';
import { api } from '@/lib/api/client';
import { LoginDialog } from './LoginDialog';

/**
 * AuthProvider component that:
 * - Initializes auth state on mount (via useAuth hook)
 * - Wires up API client callbacks for trial limit and auth required
 * - Renders the login dialog when needed
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  // useAuth internally handles auth initialization
  useAuth();
  const { auth, openLoginDialog, closeLoginDialog } = useStore();

  // Wire up API client callbacks
  useEffect(() => {
    api.setOnTrialLimitReached((message) => {
      openLoginDialog(message);
    });

    api.setOnAuthRequired(() => {
      openLoginDialog('Your session has expired. Please sign in again.');
    });
  }, [openLoginDialog]);

  return (
    <>
      {children}
      <LoginDialog
        open={auth.showLoginDialog}
        onOpenChange={(open) => {
          if (!open) closeLoginDialog();
        }}
        title="Sign in to continue"
        description={auth.loginDialogMessage || 'Create an account or sign in to create more systematic reviews.'}
      />
    </>
  );
}
