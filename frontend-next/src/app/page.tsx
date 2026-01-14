'use client';

import { AppShell } from '@/components/layout';
import { Sidebar } from '@/components/sidebar';
import { ManuscriptEditor } from '@/components/editor';
import { ChatContainer } from '@/components/chat';

export default function Home() {
  return (
    <AppShell
      sidebar={<Sidebar />}
      editor={<ManuscriptEditor />}
      chat={<ChatContainer />}
    />
  );
}
