'use client';

import { useCallback } from 'react';
import { api } from '@/lib/api/client';
import { useStore } from '@/store';
import { usePolling } from './usePolling';
import type { WorkflowCreateRequest, WorkflowResponse } from '@/types';

export function useWorkflow() {
  const {
    workflow,
    setCurrentWorkflow,
    updateWorkflow,
    addToHistory,
    setIsCreating,
    setIsPolling,
    removeFromHistory,
    setManuscript,
    setEditorLoading,
    setLayoutMode,
    startTransition,
    endTransition,
    setChatStage,
    addMessage,
  } = useStore();

  // Poll for workflow status when pending or running
  const { isPolling } = usePolling<WorkflowResponse>(
    () => api.getWorkflow(workflow.current?.id || ''),
    {
      enabled: workflow.current?.status === 'running' || workflow.current?.status === 'pending',
      interval: 5000, // 5 seconds
      shouldStop: (data) =>
        data.status === 'completed' || data.status === 'failed',
      onSuccess: async (data) => {
        updateWorkflow(data);
        setIsPolling(data.status === 'running');

        if (data.status === 'completed') {
          // Fetch manuscript when workflow completes
          setEditorLoading(true);
          try {
            const manuscript = await api.getManuscript(data.id);
            setManuscript(manuscript);

            // Transition to editor view
            startTransition();
            setTimeout(() => {
              setLayoutMode('split-view');
              setTimeout(() => {
                endTransition();
                setChatStage('complete');
                addMessage({
                  role: 'assistant',
                  content: `Your systematic review is complete! Found ${data.papers_found} papers, included ${data.papers_included} after screening. The manuscript is ready for review.`,
                });
              }, 500);
            }, 100);
          } catch (error) {
            console.error('Failed to fetch manuscript:', error);
            addMessage({
              role: 'assistant',
              content: 'Workflow completed but failed to load manuscript. Please try refreshing.',
            });
          }
        } else if (data.status === 'failed') {
          addMessage({
            role: 'assistant',
            content: `Workflow failed: ${data.error_message || 'Unknown error'}. Please try again.`,
          });
          setChatStage('confirm');
        }
      },
    }
  );

  const createWorkflow = useCallback(
    async (data: WorkflowCreateRequest): Promise<WorkflowResponse> => {
      setIsCreating(true);
      try {
        const response = await api.createWorkflow(data);
        setCurrentWorkflow(response);
        addToHistory(response);
        setIsPolling(true);
        return response;
      } finally {
        setIsCreating(false);
      }
    },
    [setIsCreating, setCurrentWorkflow, addToHistory, setIsPolling]
  );

  const loadWorkflow = useCallback(
    async (id: string) => {
      setEditorLoading(true);
      try {
        const workflowData = await api.getWorkflow(id);
        setCurrentWorkflow(workflowData);

        if (workflowData.status === 'completed') {
          const manuscript = await api.getManuscript(id);
          setManuscript(manuscript);
          setLayoutMode('split-view');
        }
      } catch (error) {
        console.error('Failed to load workflow:', error);
        throw error;
      } finally {
        setEditorLoading(false);
      }
    },
    [setCurrentWorkflow, setManuscript, setLayoutMode, setEditorLoading]
  );

  const deleteWorkflow = useCallback(
    async (id: string) => {
      await api.deleteWorkflow(id);
      removeFromHistory(id);
    },
    [removeFromHistory]
  );

  const listWorkflows = useCallback(async () => {
    const response = await api.listWorkflows();
    return response.workflows;
  }, []);

  return {
    currentWorkflow: workflow.current,
    workflowHistory: workflow.history,
    isCreating: workflow.isCreating,
    isPolling,
    createWorkflow,
    loadWorkflow,
    deleteWorkflow,
    listWorkflows,
  };
}
