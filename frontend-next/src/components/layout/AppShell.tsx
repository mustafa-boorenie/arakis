'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '@/store';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  FileText,
} from 'lucide-react';

interface AppShellProps {
  sidebar: React.ReactNode;
  editor: React.ReactNode;
  chat: React.ReactNode;
  workflowDetail?: React.ReactNode;
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

export function AppShell({ sidebar, editor, chat, workflowDetail }: AppShellProps) {
  const { layout, setMobileView, setMobileSidebarOpen } = useStore();
  const isMobile = useIsMobile();

  // Close mobile sidebar when switching to desktop
  useEffect(() => {
    if (!isMobile) {
      setMobileSidebarOpen(false);
    }
  }, [isMobile, setMobileSidebarOpen]);

  // Desktop layout with persistent sidebar
  const renderDesktopWithSidebar = (content: React.ReactNode, key: string) => (
    <motion.div
      key={key}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="h-full w-full flex"
    >
      {/* Fixed Sidebar */}
      <div className="h-full flex-shrink-0">
        {sidebar}
      </div>

      {/* Main Content */}
      <div className="flex-1 h-full overflow-hidden min-w-0 min-h-0 flex flex-col bg-gray-50">
        {content}
      </div>
    </motion.div>
  );

  return (
    <div className="h-screen w-full overflow-hidden bg-background">
      <AnimatePresence mode="wait">
        {layout.mode === 'chat-fullscreen' ? (
          // Chat mode with persistent sidebar
          // Distinguish between new review form and viewing existing workflow
          layout.viewMode === 'viewing-workflow' && workflowDetail ? (
            // Viewing existing workflow - show detail view
            isMobile ? (
              <motion.div
                key="workflow-detail-mobile"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="h-full w-full flex flex-col min-h-0 overflow-hidden"
              >
                {workflowDetail}
              </motion.div>
            ) : (
              renderDesktopWithSidebar(
                <div className="flex-1 h-full overflow-hidden">
                  {workflowDetail}
                </div>,
                'workflow-detail-desktop'
              )
            )
          ) : (
            // New review - show chat form flow
            isMobile ? (
              <motion.div
                key="chat-fullscreen-mobile"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="h-full w-full flex flex-col min-h-0 overflow-hidden"
              >
                {chat}
              </motion.div>
            ) : (
              renderDesktopWithSidebar(
                <div className="flex-1 h-full overflow-hidden">
                  <div className="w-full h-full flex flex-col min-h-0">
                    {chat}
                  </div>
                </div>,
                'chat-fullscreen-desktop'
              )
            )
          )
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
                <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-purple-800 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">A</span>
                </div>
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
                    key="mobile-chat"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                    className="h-full"
                  >
                    {chat}
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
          // Desktop split-view (with editor)
          <motion.div
            key="desktop-split-view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-full w-full flex"
          >
            {/* Fixed Sidebar */}
            <div className="h-full flex-shrink-0">
              {sidebar}
            </div>

            {/* Editor */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.1, ease: [0.32, 0.72, 0, 1] }}
              className="flex-1 h-full overflow-hidden min-w-0 bg-gray-50"
            >
              {editor}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
