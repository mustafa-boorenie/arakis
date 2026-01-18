'use client';

import { useEffect } from 'react';
import { AppShell } from '@/components/layout';
import { Sidebar } from '@/components/sidebar';
import { ManuscriptEditor } from '@/components/editor';
import { ChatContainer, LandingView } from '@/components/chat';
import { useStore } from '@/store';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/types';

function LandingWrapper() {
  const { addMessage, setChatStage, updateFormData, setLayoutMode } = useStore();

  const handleSubmit = (question: string) => {
    // Set the research question
    updateFormData({ research_question: question });
    // Add user message
    addMessage({ role: 'user', content: question });
    // Add assistant response
    addMessage({
      role: 'assistant',
      content: "Great question! Now, what are your inclusion criteria? Enter them as comma-separated values (e.g., 'Adult patients, RCTs, English language').",
    });
    // Move to inclusion stage
    setChatStage('inclusion');
    // Switch to chat-fullscreen mode for the rest of the flow
    setLayoutMode('chat-fullscreen');
  };

  return <LandingView onSubmit={handleSubmit} />;
}

export default function Home() {
  const setTokens = useStore((state) => state.setTokens);
  const setAuthLoading = useStore((state) => state.setAuthLoading);

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

  return (
    <AppShell
      sidebar={<Sidebar />}
      editor={<ManuscriptEditor />}
      chat={<ChatContainer />}
      landing={<LandingWrapper />}
    />
  );
}
