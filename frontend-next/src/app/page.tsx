'use client';

import { useEffect } from 'react';
import { AppShell } from '@/components/layout';
import { Sidebar } from '@/components/sidebar';
import { ManuscriptEditor } from '@/components/editor';
import { ChatContainer } from '@/components/chat';
import { WorkflowDetailView } from '@/components/workflow';
import { MarketingLandingPage } from '@/components/landing';
import { Dashboard } from '@/components/dashboard';
import { DocumentsList } from '@/components/documents';
import { useStore } from '@/store';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/types';

export default function Home() {
  const setTokens = useStore((state) => state.setTokens);
  const setAuthLoading = useStore((state) => state.setAuthLoading);
  const layoutMode = useStore((state) => state.layout.mode);
  const currentView = useStore((state) => state.layout.currentView);
  const chatStage = useStore((state) => state.chat.stage);
  const { setLayoutMode } = useStore();

  // Handle OAuth tokens in URL hash (fallback if redirected to / instead of /auth/success)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const hash = window.location.hash.substring(1);
    if (!hash) return;

    const params = new URLSearchParams(hash);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (accessToken && refreshToken) {
      // Store tokens
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      setTokens(accessToken, refreshToken);
      setAuthLoading(true);

      // Clear the hash from URL without reload
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, [setTokens, setAuthLoading]);

  const handleStartTrial = () => {
    // Switch to chat-fullscreen mode for the app
    setLayoutMode('chat-fullscreen');
  };

  // Show marketing landing page full-screen (no sidebar) when in landing mode
  if (layoutMode === 'landing') {
    return <MarketingLandingPage onStartTrial={handleStartTrial} />;
  }

  // Determine which main content to show based on currentView and chatStage
  const getMainContent = () => {
    // If viewing AI Writer documents list
    if (currentView === 'ai-writer') {
      return <DocumentsList />;
    }

    // For dashboard view, show Dashboard when at welcome/question stage
    // Otherwise show ChatContainer for the workflow creation flow
    if (currentView === 'dashboard') {
      const showDashboard = chatStage === 'welcome' || chatStage === 'question';
      return showDashboard ? <Dashboard /> : <ChatContainer />;
    }

    // Default to Dashboard for other views (placeholder)
    return <Dashboard />;
  };

  // Show app with sidebar for all other modes
  return (
    <AppShell
      sidebar={<Sidebar />}
      editor={<ManuscriptEditor />}
      chat={getMainContent()}
      workflowDetail={<WorkflowDetailView />}
    />
  );
}
