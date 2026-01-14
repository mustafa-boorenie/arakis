'use client';

import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { WorkflowCard } from './WorkflowCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { History, FileQuestion } from 'lucide-react';

export function WorkflowHistory() {
  const { workflow } = useStore();
  const { loadWorkflow, deleteWorkflow } = useWorkflow();

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
