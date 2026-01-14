'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { WorkflowCard } from './WorkflowCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { History, FileQuestion, RefreshCw, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

export function WorkflowHistory() {
  const { workflow, addToHistory } = useStore();
  const { loadWorkflow, deleteWorkflow } = useWorkflow();
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  // Load workflows from API on mount
  useEffect(() => {
    const loadFromApi = async () => {
      if (hasLoaded) return;
      setIsLoading(true);
      try {
        const response = await api.listWorkflows();
        // Add any workflows from API that aren't in local history
        for (const w of response.workflows) {
          addToHistory(w);
        }
        setHasLoaded(true);
      } catch (error) {
        console.error('Failed to load workflows:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadFromApi();
  }, [addToHistory, hasLoaded]);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const response = await api.listWorkflows();
      for (const w of response.workflows) {
        addToHistory(w);
      }
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
    try {
      await deleteWorkflow(id);
    } catch (error) {
      console.error('Failed to delete workflow:', error);
    }
  };

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
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 p-3 border-b">
        <History className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">Review History</h3>
        <span className="text-xs text-muted-foreground ml-auto">
          {workflow.history.length} review{workflow.history.length !== 1 ? 's' : ''}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={handleRefresh}
          disabled={isLoading}
          title="Refresh"
        >
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {workflow.history.map((w) => (
            <WorkflowCard
              key={w.id}
              workflow={w}
              isActive={workflow.current?.id === w.id}
              onClick={() => handleSelect(w.id)}
              onDelete={() => handleDelete(w.id)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
