'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/store';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SettingsDialog } from '@/components/settings';
import { api } from '@/lib/api/client';
import type { WorkflowResponse } from '@/types';
import {
  PenSquare,
  FileText,
  Archive,
  ArchiveRestore,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

export function Sidebar() {
  const {
    resetChat,
    workflow,
    addToHistory,
    archiveWorkflow,
    unarchiveWorkflow,
    setCurrentWorkflow,
    setManuscript,
    setLayoutMode,
    setChatStage,
    addMessage,
    setEditorLoading,
  } = useStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  // Safe access to archived array (handles undefined from old localStorage)
  const archivedIds = workflow.archived || [];

  // Filter active and archived workflows
  const activeWorkflows = workflow.history.filter((w) => !archivedIds.includes(w.id));
  const archivedWorkflows = workflow.history.filter((w) => archivedIds.includes(w.id));

  // Load workflow history on mount
  useEffect(() => {
    const loadHistory = async () => {
      setIsLoading(true);
      try {
        const response = await api.listWorkflows();
        for (const w of response.workflows) {
          addToHistory(w);
        }
      } catch (error) {
        console.error('Failed to load history:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadHistory();
  }, [addToHistory]);

  // Handle clicking on a workflow
  const handleWorkflowClick = async (w: WorkflowResponse) => {
    setCurrentWorkflow(w);

    if (w.status === 'completed') {
      setEditorLoading(true);
      try {
        const manuscript = await api.getManuscript(w.id);
        setManuscript(manuscript);
        setLayoutMode('split-view');
        setChatStage('complete');
        addMessage({
          role: 'assistant',
          content: `Loaded your review: "${w.research_question}". Found ${w.papers_found} papers, included ${w.papers_included} after screening.`,
        });
      } catch (error) {
        console.error('Failed to load manuscript:', error);
      } finally {
        setEditorLoading(false);
      }
    }
  };

  // Handle archive
  const handleArchive = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    archiveWorkflow(id);
  };

  // Handle restore from archive
  const handleRestore = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    unarchiveWorkflow(id);
  };

  // Truncate text
  const truncate = (text: string, length: number) => {
    if (text.length <= length) return text;
    return text.slice(0, length) + '...';
  };

  return (
    <div className="h-full flex flex-col bg-sidebar text-sidebar-foreground">
      {/* Header */}
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-foreground/10 flex items-center justify-center">
            <FileText className="w-4 h-4" />
          </div>
          <span className="font-semibold text-sm">Arakis</span>
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </div>
        <button
          onClick={resetChat}
          className="p-2 hover:bg-sidebar-accent rounded-lg transition-colors"
          title="New Review"
        >
          <PenSquare className="w-5 h-5" />
        </button>
      </div>

      {/* Menu Items */}
      <div className="px-2 space-y-1">
        <button
          onClick={resetChat}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-sidebar-accent rounded-lg transition-colors text-left"
        >
          <PenSquare className="w-4 h-4" />
          New review
        </button>
        <SettingsDialog />
      </div>

      {/* Divider */}
      <div className="my-3 border-t border-sidebar-border" />

      {/* Active Reviews */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="px-4 py-2">
          <span className="text-xs text-muted-foreground font-medium">Your reviews</span>
        </div>

        <ScrollArea className="flex-1">
          <div className="px-2 space-y-0.5">
            {isLoading ? (
              <div className="px-3 py-2 text-sm text-muted-foreground">
                Loading...
              </div>
            ) : activeWorkflows.length === 0 ? (
              <div className="px-3 py-2 text-sm text-muted-foreground">
                No reviews yet
              </div>
            ) : (
              activeWorkflows.map((w) => (
                <div
                  key={w.id}
                  onClick={() => handleWorkflowClick(w)}
                  onMouseEnter={() => setHoveredId(w.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`
                    group flex items-center justify-between gap-2 px-3 py-2
                    rounded-lg cursor-pointer transition-colors
                    ${workflow.current?.id === w.id
                      ? 'bg-sidebar-accent'
                      : 'hover:bg-sidebar-accent'
                    }
                  `}
                >
                  <span className="text-sm truncate flex-1">
                    {truncate(w.research_question, 30)}
                  </span>
                  {hoveredId === w.id && (
                    <button
                      onClick={(e) => handleArchive(e, w.id)}
                      className="p-1 hover:bg-muted rounded transition-colors flex-shrink-0"
                      title="Archive"
                    >
                      <Archive className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                    </button>
                  )}
                </div>
              ))
            )}

            {/* Archived Section */}
            {archivedWorkflows.length > 0 && (
              <>
                <div className="mt-4 mb-1">
                  <button
                    onClick={() => setShowArchived(!showArchived)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showArchived ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                    <Archive className="w-3.5 h-3.5" />
                    <span>Archived ({archivedWorkflows.length})</span>
                  </button>
                </div>

                {showArchived && (
                  <div className="space-y-0.5 opacity-60">
                    {archivedWorkflows.map((w) => (
                      <div
                        key={w.id}
                        onClick={() => handleWorkflowClick(w)}
                        onMouseEnter={() => setHoveredId(w.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        className={`
                          group flex items-center justify-between gap-2 px-3 py-2
                          rounded-lg cursor-pointer transition-colors
                          hover:bg-sidebar-accent hover:opacity-100
                        `}
                      >
                        <span className="text-sm truncate flex-1">
                          {truncate(w.research_question, 30)}
                        </span>
                        {hoveredId === w.id && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={(e) => handleRestore(e, w.id)}
                              className="p-1 hover:bg-muted rounded transition-colors"
                              title="Restore"
                            >
                              <ArchiveRestore className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* User Profile */}
      <div className="p-2 border-t border-sidebar-border">
        <button className="w-full flex items-center gap-3 px-3 py-2 hover:bg-sidebar-accent rounded-lg transition-colors">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center text-white text-xs font-medium">
            U
          </div>
          <div className="flex-1 text-left">
            <span className="text-sm">User</span>
          </div>
        </button>
      </div>
    </div>
  );
}
