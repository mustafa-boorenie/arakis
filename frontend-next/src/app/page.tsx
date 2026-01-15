'use client';

import { AppShell } from '@/components/layout';
import { Sidebar } from '@/components/sidebar';
import { ManuscriptEditor } from '@/components/editor';
import { ChatContainer, LandingView } from '@/components/chat';
import { useStore } from '@/store';

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
  return (
    <AppShell
      sidebar={<Sidebar />}
      editor={<ManuscriptEditor />}
      chat={<ChatContainer />}
      landing={<LandingWrapper />}
    />
  );
}
