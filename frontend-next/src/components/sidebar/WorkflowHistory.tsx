'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { WorkflowCard } from './WorkflowCard';
import { Button } from '@/components/ui/button';
import { History, FileQuestion, RefreshCw, Loader2, Archive, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '@/lib/api/client';

export function WorkflowHistory() {
  const { workflow, setHistory, archiveWorkflow, unarchiveWorkflow } = useStore();
  const { loadWorkflow, deleteWorkflow } = useWorkflow();
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  // Load workflows from API on mount
  useEffect(() => {
    const loadFromApi = async () => {
      if (hasLoaded) return;
      setIsLoading(true);
      try {
        const response = await api.listWorkflows();
        // Replace history with fresh data from API
        setHistory(response.workflows);
        setHasLoaded(true);
      } catch (error) {
        console.error('Failed to load workflows:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadFromApi();
  }, [setHistory, hasLoaded]);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const response = await api.listWorkflows();
      // Replace history with fresh data from API
      setHistory(response.workflows);
    } catch (error) {
      console.error('Failed to refresh workflows:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = async (id: string) => {
    try {
      await loadWorkflow(id);
    } catch (error) {
      console.error('Failed to load workflow:', error);
    }
  };

  const handleDelete = async (id: string) => {
    // Find the workflow to show in confirmation
    const workflowToDelete = workflow.history.find((w) => w.id === id);
    const question = workflowToDelete?.research_question || 'this review';

    if (!window.confirm(`Are you sure you want to delete "${question}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      await deleteWorkflow(id);
    } catch (error) {
      console.error('Failed to delete workflow:', error);
    }
  };

  const handleArchive = (id: string) => {
    const isCurrentlyArchived = workflow.archived?.includes(id);
    if (isCurrentlyArchived) {
      unarchiveWorkflow(id);
    } else {
      archiveWorkflow(id);
    }
  };

  // Separate active and archived workflows
  const archivedIds = workflow.archived || [];
  const activeWorkflows = workflow.history.filter((w) => !archivedIds.includes(w.id));
  const archivedWorkflows = workflow.history.filter((w) => archivedIds.includes(w.id));

  if (isLoading && workflow.history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4 text-center">
        <Loader2 className="w-8 h-8 text-muted-foreground mb-3 animate-spin" />
        <p className="text-sm text-muted-foreground">
          Loading workflows...
        </p>
      </div>
    );
  }

  if (workflow.history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4 text-center">
        <FileQuestion className="w-12 h-12 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">
          No previous reviews yet.
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Your review history will appear here.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={handleRefresh}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2" />
          )}
          Refresh
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center gap-2 p-4 border-b bg-white">
        <History className="w-5 h-5 text-purple-600" />
        <h3 className="text-lg font-semibold">My Reviews</h3>
        <span className="text-sm text-muted-foreground ml-auto">
          {workflow.history.length} review{workflow.history.length !== 1 ? 's' : ''}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={handleRefresh}
          disabled={isLoading}
          title="Refresh"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-3 max-w-4xl mx-auto">
          {/* Active workflows */}
          {activeWorkflows.map((w) => (
            <WorkflowCard
              key={w.id}
              workflow={w}
              isActive={workflow.current?.id === w.id}
              isArchived={false}
              onClick={() => handleSelect(w.id)}
              onDelete={() => handleDelete(w.id)}
              onArchive={() => handleArchive(w.id)}
            />
          ))}

          {/* Archived section */}
          {archivedWorkflows.length > 0 && (
            <div className="pt-4">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-between text-muted-foreground hover:text-foreground"
                onClick={() => setShowArchived(!showArchived)}
              >
                <span className="flex items-center gap-2">
                  <Archive className="w-4 h-4" />
                  Archived ({archivedWorkflows.length})
                </span>
                {showArchived ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>

              {showArchived && (
                <div className="mt-3 space-y-3">
                  {archivedWorkflows.map((w) => (
                    <WorkflowCard
                      key={w.id}
                      workflow={w}
                      isActive={workflow.current?.id === w.id}
                      isArchived={true}
                      onClick={() => handleSelect(w.id)}
                      onDelete={() => handleDelete(w.id)}
                      onArchive={() => handleArchive(w.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty state for active workflows */}
          {activeWorkflows.length === 0 && archivedWorkflows.length > 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              All reviews are archived
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
