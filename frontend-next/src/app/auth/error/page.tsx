'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { XCircle, ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

function AuthErrorContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const error = searchParams.get('error') || 'authentication_failed';
  const errorDescription = searchParams.get('error_description') || 'An error occurred during sign in.';

  const getErrorTitle = (error: string) => {
    switch (error) {
      case 'access_denied':
        return 'Access Denied';
      case 'invalid_request':
        return 'Invalid Request';
      case 'temporarily_unavailable':
        return 'Service Unavailable';
      case 'server_error':
        return 'Server Error';
      case 'invalid_state':
        return 'Session Expired';
      default:
        return 'Authentication Failed';
    }
  };

  const getErrorMessage = (error: string, description: string) => {
    switch (error) {
      case 'access_denied':
        return 'You declined the sign in request or the request was cancelled.';
      case 'invalid_state':
        return 'Your session has expired. Please try signing in again.';
      case 'temporarily_unavailable':
        return 'The authentication service is temporarily unavailable. Please try again later.';
      default:
        return description;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-6 p-8 max-w-md">
        <XCircle className="w-16 h-16 text-destructive mx-auto" />

        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">{getErrorTitle(error)}</h1>
          <p className="text-muted-foreground">
            {getErrorMessage(error, errorDescription)}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
          <Button
            variant="outline"
            onClick={() => router.push('/')}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Return home
          </Button>
          <Button
            onClick={() => router.back()}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </Button>
        </div>

        <p className="text-xs text-muted-foreground pt-4">
          If this problem persists, please contact support.
        </p>
      </div>
    </div>
  );
}

function AuthErrorLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={<AuthErrorLoading />}>
      <AuthErrorContent />
    </Suspense>
  );
}
