'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

function AuthSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { handleOAuthCallback } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Get tokens from URL hash fragment
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);

        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');

        if (!accessToken || !refreshToken) {
          // Check if tokens are in query params instead (some OAuth flows)
          const queryAccessToken = searchParams.get('access_token');
          const queryRefreshToken = searchParams.get('refresh_token');

          if (!queryAccessToken || !queryRefreshToken) {
            throw new Error('Missing authentication tokens');
          }

          await handleOAuthCallback(queryAccessToken, queryRefreshToken);
        } else {
          await handleOAuthCallback(accessToken, refreshToken);
        }

        setStatus('success');

        // Get redirect URL from state or default to home
        const returnTo = searchParams.get('return_to') || '/';

        // Short delay to show success message
        setTimeout(() => {
          router.push(returnTo);
        }, 1500);
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('error');
        setErrorMessage(
          error instanceof Error ? error.message : 'Authentication failed'
        );
      }
    };

    processCallback();
  }, [handleOAuthCallback, router, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4 p-8">
        {status === 'loading' && (
          <>
            <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
            <h1 className="text-xl font-semibold">Completing sign in...</h1>
            <p className="text-muted-foreground">Please wait while we verify your account.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
            <h1 className="text-xl font-semibold">Sign in successful!</h1>
            <p className="text-muted-foreground">Redirecting you back...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-12 h-12 text-destructive mx-auto" />
            <h1 className="text-xl font-semibold">Sign in failed</h1>
            <p className="text-muted-foreground">{errorMessage}</p>
            <button
              onClick={() => router.push('/')}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Return to home
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function AuthSuccessLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4 p-8">
        <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
        <h1 className="text-xl font-semibold">Completing sign in...</h1>
        <p className="text-muted-foreground">Please wait while we verify your account.</p>
      </div>
    </div>
  );
}

export default function AuthSuccessPage() {
  return (
    <Suspense fallback={<AuthSuccessLoading />}>
      <AuthSuccessContent />
    </Suspense>
  );
}
