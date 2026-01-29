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
    setViewMode,
    startTransition,
    endTransition,
    setChatStage,
    addMessage,
  } = useStore();

  // Poll for workflow status when pending or running
  const workflowId = workflow.current?.id;
  const workflowStatus = workflow.current?.status;
  const shouldPoll = !!(workflowId) && (workflowStatus === 'running' || workflowStatus === 'pending');

  const { isPolling } = usePolling<WorkflowResponse>(
    async () => {
      if (!workflowId) {
        throw new Error('No workflow ID');
      }
      return api.getWorkflow(workflowId);
    },
    {
      enabled: shouldPoll,
      interval: 5000, // 5 seconds
      shouldStop: (data) =>
        data.status === 'completed' || data.status === 'failed' || data.status === 'needs_review',
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
        } else if (data.status === 'needs_review') {
          addMessage({
            role: 'assistant',
            content: `Workflow needs your attention: ${data.action_required || 'Please review and click Resume to continue.'}`,
          });
        }
      },
      onError: (error) => {
        // Handle 404 errors - workflow no longer exists on server
        console.error('Polling error:', error);
        if (workflow.current) {
          // Mark the workflow as failed in local state
          updateWorkflow({
            ...workflow.current,
            status: 'failed',
            error_message: 'Workflow no longer exists on server',
          });
        }
        setIsPolling(false);
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
        // Switch to workflow detail view to show progress
        setViewMode('viewing-workflow');
        return response;
      } finally {
        setIsCreating(false);
      }
    },
    [setIsCreating, setCurrentWorkflow, addToHistory, setIsPolling, setViewMode]
  );

  const loadWorkflow = useCallback(
    async (id: string) => {
      setEditorLoading(true);
      try {
        const workflowData = await api.getWorkflow(id);
        setCurrentWorkflow(workflowData);

        if (workflowData.status === 'completed') {
          // For completed workflows, fetch manuscript and show split-view editor
          const manuscript = await api.getManuscript(id);
          setManuscript(manuscript);
          setLayoutMode('split-view');
        } else {
          // For running/pending/failed workflows, show the detail view
          setLayoutMode('chat-fullscreen');
          setViewMode('viewing-workflow');

          // Start polling if workflow is still running
          if (workflowData.status === 'running' || workflowData.status === 'pending') {
            setIsPolling(true);
          }
        }
      } catch (error) {
        console.error('Failed to load workflow:', error);
        throw error;
      } finally {
        setEditorLoading(false);
      }
    },
    [setCurrentWorkflow, setManuscript, setLayoutMode, setEditorLoading, setViewMode, setIsPolling]
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

  const resumeWorkflow = useCallback(
    async (id: string) => {
      try {
        const response = await api.resumeWorkflow(id);
        setCurrentWorkflow(response);
        setIsPolling(true);
        addMessage({
          role: 'assistant',
          content: 'Resuming workflow...',
        });
        return response;
      } catch (error) {
        console.error('Failed to resume workflow:', error);
        addMessage({
          role: 'assistant',
          content: 'Failed to resume workflow. Please try again.',
        });
        throw error;
      }
    },
    [setCurrentWorkflow, setIsPolling, addMessage]
  );

  const rerunStage = useCallback(
    async (workflowId: string, stage: string, inputOverride?: Record<string, unknown>) => {
      try {
        const response = await api.rerunStage(workflowId, stage, inputOverride);
        if (response.success) {
          // Refresh workflow data
          const workflowData = await api.getWorkflow(workflowId);
          setCurrentWorkflow(workflowData);
          setIsPolling(workflowData.status === 'running');
          addMessage({
            role: 'assistant',
            content: `Stage "${stage}" has been rerun successfully.`,
          });
        } else {
          addMessage({
            role: 'assistant',
            content: `Stage "${stage}" failed: ${response.error || 'Unknown error'}`,
          });
        }
        return response;
      } catch (error) {
        console.error('Failed to rerun stage:', error);
        addMessage({
          role: 'assistant',
          content: `Failed to rerun stage "${stage}". Please try again.`,
        });
        throw error;
      }
    },
    [setCurrentWorkflow, setIsPolling, addMessage]
  );

  const getStageCheckpoints = useCallback(async (id: string) => {
    return api.getStageCheckpoints(id);
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
    resumeWorkflow,
    rerunStage,
    getStageCheckpoints,
  };
}
