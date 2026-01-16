'use client';

import { useStore } from '@/store';
import { useAuth } from '@/hooks';
import { Button } from '@/components/ui/button';
import { LoginButtons, UserMenu } from '@/components/auth';
import { PlusCircle, FileText } from 'lucide-react';

export function Header() {
  const { resetChat, layout } = useStore();
  const { user, isAuthenticated, isLoading } = useAuth();

  return (
    <header className="h-14 border-b bg-background flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <FileText className="w-6 h-6 text-primary" />
        <h1 className="font-semibold text-lg">Arakis</h1>
        <span className="text-xs text-muted-foreground">
          Systematic Review Assistant
        </span>
      </div>

      <div className="flex items-center gap-3">
        {layout.mode === 'split-view' && (
          <Button variant="outline" size="sm" onClick={resetChat}>
            <PlusCircle className="w-4 h-4 mr-2" />
            New Review
          </Button>
        )}

        {/* Auth UI */}
        {!isLoading && (
          isAuthenticated && user ? (
            <UserMenu />
          ) : (
            <LoginButtons variant="compact" showText={false} />
          )
        )}
      </div>
    </header>
  );
}
