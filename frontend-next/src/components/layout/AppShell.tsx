'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '@/store';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  FileText,
} from 'lucide-react';

interface AppShellProps {
  sidebar: React.ReactNode;
  editor: React.ReactNode;
  chat: React.ReactNode;
}

// Hook to detect mobile screen
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  return isMobile;
}

export function AppShell({ sidebar, editor, chat }: AppShellProps) {
  const { layout, setMobileView, setMobileSidebarOpen } = useStore();
  const isMobile = useIsMobile();

  // Close mobile sidebar when switching to desktop
  useEffect(() => {
    if (!isMobile) {
      setMobileSidebarOpen(false);
    }
  }, [isMobile, setMobileSidebarOpen]);

  return (
    <div className="h-screen w-full overflow-hidden bg-background">
      <AnimatePresence mode="wait">
        {layout.mode === 'chat-fullscreen' ? (
          // Full-screen chat mode (same for mobile and desktop)
          <motion.div
            key="chat-fullscreen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full w-full flex items-center justify-center px-2 sm:px-4 md:px-8 lg:px-12"
          >
            <div className="w-full max-w-2xl lg:max-w-3xl xl:max-w-4xl 2xl:max-w-5xl h-full flex flex-col">
              {chat}
            </div>
          </motion.div>
        ) : isMobile ? (
          // Mobile split-view: tabs to switch between sidebar and editor
          <motion.div
            key="mobile-split-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full w-full flex flex-col"
          >
            {/* Mobile Header */}
            <div className="flex-shrink-0 h-12 border-b bg-background flex items-center justify-between px-2 gap-2">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                <span className="font-semibold text-sm">Arakis</span>
              </div>

              {/* Mobile View Toggle */}
              <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                <Button
                  variant={layout.mobileView === 'sidebar' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-3 text-xs gap-1.5"
                  onClick={() => setMobileView('sidebar')}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Chat
                </Button>
                <Button
                  variant={layout.mobileView === 'editor' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-3 text-xs gap-1.5"
                  onClick={() => setMobileView('editor')}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Editor
                </Button>
              </div>
            </div>

            {/* Mobile Content */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <AnimatePresence mode="wait">
                {layout.mobileView === 'sidebar' ? (
                  <motion.div
                    key="mobile-sidebar"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                    className="h-full"
                  >
                    {sidebar}
                  </motion.div>
                ) : (
                  <motion.div
                    key="mobile-editor"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.2 }}
                    className="h-full"
                  >
                    {editor}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        ) : (
          // Desktop split-view
          <motion.div
            key="desktop-split-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full w-full flex"
          >
            {/* Sidebar */}
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: layout.sidebarWidth, opacity: 1 }}
              transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
              className={cn(
                'h-full flex-shrink-0 border-r bg-muted/30',
                'min-w-[300px] max-w-[450px]',
                layout.isTransitioning && 'pointer-events-none'
              )}
              style={{ width: layout.sidebarWidth }}
            >
              {sidebar}
            </motion.div>

            {/* Editor */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.1, ease: [0.32, 0.72, 0, 1] }}
              className="flex-1 h-full overflow-hidden min-w-0"
            >
              {editor}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
