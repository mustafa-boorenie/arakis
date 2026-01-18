'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '@/store';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  FileText,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react';

interface AppShellProps {
  sidebar: React.ReactNode;
  editor: React.ReactNode;
  chat: React.ReactNode;
  landing?: React.ReactNode;
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

// Collapsible Sidebar wrapper
function CollapsibleSidebar({
  children,
  isCollapsed,
  width,
}: {
  children: React.ReactNode;
  isCollapsed: boolean;
  width: number;
}) {
  return (
    <motion.div
      initial={false}
      animate={{
        width: isCollapsed ? 0 : width,
        opacity: isCollapsed ? 0 : 1,
      }}
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      className={cn(
        'h-full flex-shrink-0 border-r border-border bg-sidebar overflow-hidden',
        isCollapsed && 'border-r-0'
      )}
    >
      <div style={{ width }} className="h-full">
        {children}
      </div>
    </motion.div>
  );
}

// Sidebar toggle button
function SidebarToggle({
  isCollapsed,
  onToggle,
}: {
  isCollapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'absolute z-50 p-2 rounded-lg',
        'bg-background/80 backdrop-blur border border-border',
        'hover:bg-muted transition-colors',
        'text-muted-foreground hover:text-foreground',
        isCollapsed ? 'left-3' : 'left-[270px]'
      )}
      style={{
        top: 32,
        left: isCollapsed ? 12 : 248,
        transition: 'left 0.2s ease',
      }}
      title={isCollapsed ? 'Show sidebar' : 'Hide sidebar'}
    >
      {isCollapsed ? (
        <PanelLeft className="w-4 h-4" />
      ) : (
        <PanelLeftClose className="w-4 h-4" />
      )}
    </button>
  );
}

export function AppShell({ sidebar, editor, chat, landing, workflowDetail }: AppShellProps) {
  const { layout, setMobileView, setMobileSidebarOpen, toggleSidebarCollapsed } = useStore();
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
      className="h-full w-full flex relative"
    >
      {/* Sidebar Toggle Button */}
      <SidebarToggle
        isCollapsed={layout.isSidebarCollapsed}
        onToggle={toggleSidebarCollapsed}
      />

      {/* Collapsible Sidebar */}
      <CollapsibleSidebar
        isCollapsed={layout.isSidebarCollapsed}
        width={layout.sidebarWidth}
      >
        {sidebar}
      </CollapsibleSidebar>

      {/* Main Content */}
      <div className="flex-1 h-full overflow-hidden min-w-0 min-h-0 flex flex-col">
        {content}
      </div>
    </motion.div>
  );

  return (
    <div className="h-screen w-full overflow-hidden bg-background">
      <AnimatePresence mode="wait">
        {layout.mode === 'landing' ? (
          // Landing mode with sidebar + centered input (ChatGPT style)
          isMobile ? (
            // Mobile: just show landing view full screen
            <motion.div
              key="landing-mobile"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="h-full w-full flex flex-col"
            >
              {landing || chat}
            </motion.div>
          ) : (
            // Desktop: sidebar + landing view
            renderDesktopWithSidebar(landing || chat, 'landing-desktop')
          )
        ) : layout.mode === 'chat-fullscreen' ? (
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
            className="h-full w-full flex relative"
          >
            {/* Sidebar Toggle Button */}
            <SidebarToggle
              isCollapsed={layout.isSidebarCollapsed}
              onToggle={toggleSidebarCollapsed}
            />

            {/* Collapsible Sidebar */}
            <CollapsibleSidebar
              isCollapsed={layout.isSidebarCollapsed}
              width={layout.sidebarWidth}
            >
              {sidebar}
            </CollapsibleSidebar>

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
