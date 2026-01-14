'use client';

import { useEffect, useRef, useLayoutEffect, useState } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { DatabaseSelector } from './DatabaseSelector';
import { WorkflowProgress } from './WorkflowProgress';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sparkles, History, FileText, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { WorkflowCreateRequest, WorkflowResponse } from '@/types';

const CHAT_PROMPTS = {
  welcome:
    "Welcome to Arakis! I'll help you create a systematic review. What research question would you like to investigate?",
  inclusion:
    "Great question! Now, what are your inclusion criteria? Enter them as comma-separated values (e.g., 'Adult patients, RCTs, English language').",
  exclusion:
    "Got it. What are your exclusion criteria? Again, comma-separated values work best.",
  databases:
    'Which databases would you like to search? Select at least one below.',
  confirm:
    "Perfect! Here's a summary of your review. Click 'Start Review' when you're ready.",
  creating:
    'Starting your systematic review... This may take a few minutes depending on the number of results.',
};

export function ChatContainer() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyWorkflows, setHistoryWorkflows] = useState<WorkflowResponse[]>([]);
  const {
    chat,
    addMessage,
    setChatStage,
    updateFormData,
    workflow,
    layout,
    setLayoutMode,
    setManuscript,
    setCurrentWorkflow,
    addToHistory,
    setEditorLoading,
  } = useStore();
  const { createWorkflow, isCreating } = useWorkflow();

  // Load history when drawer opens
  const handleOpenHistory = async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    try {
      const response = await api.listWorkflows();
      setHistoryWorkflows(response.workflows);
      // Also add to store
      for (const w of response.workflows) {
        addToHistory(w);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Load a workflow from history
  const handleLoadWorkflow = async (w: WorkflowResponse) => {
    setHistoryOpen(false);
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
        addMessage({
          role: 'assistant',
          content: 'Failed to load manuscript. Please try again.',
        });
      } finally {
        setEditorLoading(false);
      }
    }
  };

  // Initialize with welcome message
  useEffect(() => {
    if (chat.messages.length === 0 && chat.stage === 'welcome') {
      addMessage({
        role: 'assistant',
        content: CHAT_PROMPTS.welcome,
      });
      setChatStage('question');
    }
  }, [chat.messages.length, chat.stage, addMessage, setChatStage]);

  // Auto-scroll to bottom on new messages or stage changes
  useLayoutEffect(() => {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }, [chat.messages, chat.stage]);

  const handleUserMessage = async (message: string) => {
    addMessage({ role: 'user', content: message });

    switch (chat.stage) {
      case 'question':
        updateFormData({ research_question: message });
        addMessage({ role: 'assistant', content: CHAT_PROMPTS.inclusion });
        setChatStage('inclusion');
        break;

      case 'inclusion':
        updateFormData({ inclusion_criteria: message });
        addMessage({ role: 'assistant', content: CHAT_PROMPTS.exclusion });
        setChatStage('exclusion');
        break;

      case 'exclusion':
        updateFormData({ exclusion_criteria: message });
        addMessage({ role: 'assistant', content: CHAT_PROMPTS.databases });
        setChatStage('databases');
        break;

      default:
        break;
    }
  };

  const handleDatabaseConfirm = () => {
    addMessage({
      role: 'user',
      content: `Selected databases: ${chat.formData.databases.join(', ')}`,
    });
    addMessage({ role: 'assistant', content: CHAT_PROMPTS.confirm });
    setChatStage('confirm');
  };

  const handleStartReview = async () => {
    setChatStage('creating');
    addMessage({
      role: 'assistant',
      content: CHAT_PROMPTS.creating,
      metadata: { isLoading: true },
    });

    try {
      const request: WorkflowCreateRequest = {
        research_question: chat.formData.research_question,
        inclusion_criteria: chat.formData.inclusion_criteria,
        exclusion_criteria: chat.formData.exclusion_criteria,
        databases: chat.formData.databases,
        max_results_per_query: chat.formData.max_results_per_query,
        fast_mode: chat.formData.fast_mode,
      };
      await createWorkflow(request);
      addMessage({
        role: 'assistant',
        content:
          'Workflow created! I\'ll keep you updated on the progress below.',
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred';
      addMessage({
        role: 'assistant',
        content: `Failed to create workflow: ${errorMessage}. Please try again.`,
      });
      setChatStage('confirm');
    }
  };

  const isInputDisabled =
    chat.stage === 'databases' ||
    chat.stage === 'confirm' ||
    chat.stage === 'creating' ||
    chat.stage === 'complete';

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header - only show in fullscreen chat mode */}
      {layout.mode === 'chat-fullscreen' && (
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            <span className="font-semibold">Arakis</span>
          </div>
          <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
            <DialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleOpenHistory}
              >
                <History className="w-4 h-4" />
                History
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[80vh]">
              <DialogHeader>
                <DialogTitle>Review History</DialogTitle>
              </DialogHeader>
              <ScrollArea className="h-[60vh] mt-4">
                {historyLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : historyWorkflows.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No previous reviews found.</p>
                  </div>
                ) : (
                  <div className="space-y-3 pr-4">
                    {historyWorkflows.map((w) => (
                      <Card
                        key={w.id}
                        className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => handleLoadWorkflow(w)}
                      >
                        <p className="font-medium text-sm line-clamp-2">
                          {w.research_question}
                        </p>
                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                              w.status === 'completed'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : w.status === 'failed'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            }`}
                          >
                            {w.status}
                          </span>
                          <span>{w.papers_found} papers found</span>
                          <span>{w.papers_included} included</span>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </DialogContent>
          </Dialog>
        </div>
      )}

      {/* Messages - scrollable container */}
      <div
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6 lg:p-8 scroll-smooth"
      >
        <div className="space-y-4 max-w-full mx-auto">
          {chat.messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Database selector */}
          {chat.stage === 'databases' && (
            <DatabaseSelector
              selected={chat.formData.databases}
              onChange={(databases) => updateFormData({ databases })}
              onConfirm={handleDatabaseConfirm}
            />
          )}

          {/* Confirmation card */}
          {chat.stage === 'confirm' && (
            <Card className="p-4 space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
              <h3 className="font-semibold">Review Summary</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Research Question:</span>
                  <p className="font-medium">{chat.formData.research_question}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Inclusion Criteria:</span>
                  <p>{chat.formData.inclusion_criteria}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Exclusion Criteria:</span>
                  <p>{chat.formData.exclusion_criteria}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Databases:</span>
                  <p>{chat.formData.databases.join(', ')}</p>
                </div>
              </div>
              <Button
                onClick={handleStartReview}
                disabled={isCreating}
                className="w-full gap-2"
              >
                <Sparkles className="w-4 h-4" />
                {isCreating ? 'Creating...' : 'Start Review'}
              </Button>
            </Card>
          )}

          {/* Workflow progress */}
          {(chat.stage === 'creating' || workflow.current) &&
            workflow.current?.status !== 'completed' && (
              <WorkflowProgress />
            )}

          {/* Invisible element at bottom for auto-scroll */}
          <div ref={bottomRef} className="h-1" />
        </div>
      </div>

      {/* Input */}
      <ChatInput
        onSubmit={handleUserMessage}
        placeholder={
          chat.stage === 'question'
            ? 'Enter your research question...'
            : chat.stage === 'inclusion'
              ? 'Enter inclusion criteria (comma-separated)...'
              : chat.stage === 'exclusion'
                ? 'Enter exclusion criteria (comma-separated)...'
                : 'Type your message...'
        }
        disabled={isInputDisabled}
      />
    </div>
  );
}
