'use client';

import { useEffect, useRef, useLayoutEffect } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { DatabaseSelector } from './DatabaseSelector';
import { WorkflowProgress } from './WorkflowProgress';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Sparkles, LogIn } from 'lucide-react';
import type { WorkflowCreateRequest } from '@/types';

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

const EXAMPLE_PROMPTS: Record<string, string[]> = {
  inclusion: [
    'Adult patients, RCTs, English language, Published after 2010',
    'Human studies, Peer-reviewed, Full-text available',
    'Prospective studies, Sample size > 50, Primary outcome reported',
  ],
  exclusion: [
    'Animal studies, Case reports, Reviews, Editorials',
    'Pediatric population, Non-English, Abstracts only',
    'Unpublished data, Duplicate publications, Conference abstracts',
  ],
};

export function ChatContainer() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const chat = useStore((state) => state.chat);
  const addMessage = useStore((state) => state.addMessage);
  const setChatStage = useStore((state) => state.setChatStage);
  const updateFormData = useStore((state) => state.updateFormData);
  const workflow = useStore((state) => state.workflow);
  const layout = useStore((state) => state.layout);
  const openLoginDialog = useStore((state) => state.openLoginDialog);

  // Use individual selectors for auth to ensure re-renders on changes
  const isAuthenticated = useStore((state) => state.auth.isAuthenticated);
  const isAuthLoading = useStore((state) => state.auth.isLoading);
  const user = useStore((state) => state.auth.user);

  const { createWorkflow, isCreating } = useWorkflow();

  // Initialize or restore chat state
  useEffect(() => {
    // Skip initialization if we're in landing mode - LandingView handles the first step
    if (layout.mode === 'landing') return;

    // If returning from OAuth with form data but no messages, restore the confirm view
    if (chat.messages.length === 0 && chat.stage === 'confirm' && chat.formData.research_question) {
      addMessage({
        role: 'assistant',
        content: "Welcome back! Here's your review summary. Click 'Start Review' to begin.",
      });
      return;
    }

    // Normal initialization for fresh start
    if (chat.messages.length === 0 && chat.stage === 'welcome') {
      addMessage({
        role: 'assistant',
        content: CHAT_PROMPTS.welcome,
      });
      setChatStage('question');
    }
  }, [chat.messages.length, chat.stage, chat.formData.research_question, addMessage, setChatStage, layout.mode]);

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

  // Check if user can start review (authenticated or auth still loading with tokens)
  const canStartReview = isAuthenticated || user !== null;

  const handleStartReview = async () => {
    // Check if user is authenticated before starting the review
    // Also allow if auth is still loading (user just logged in, profile being fetched)
    if (!canStartReview && !isAuthLoading) {
      openLoginDialog('Sign in to start your systematic review. Your progress has been saved.');
      return;
    }

    // If auth is loading, wait for it to complete (max 10 seconds with polling)
    if (isAuthLoading) {
      const maxWaitTime = 10000;
      const pollInterval = 100;
      const startTime = Date.now();

      while (Date.now() - startTime < maxWaitTime) {
        // Get fresh state from store
        const { auth } = useStore.getState();
        if (!auth.isLoading) {
          break;
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }

      // Re-check auth state after waiting
      const { auth } = useStore.getState();
      if (!auth.isAuthenticated && !auth.user) {
        openLoginDialog('Sign in to start your systematic review. Your progress has been saved.');
        return;
      }
    }

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
    <div className="flex flex-col h-full min-h-0 w-full">
      {/* Messages - scrollable container */}
      <div
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6 lg:p-8 scroll-smooth w-full"
      >
        <div className="space-y-4 w-full">
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
                disabled={isCreating || isAuthLoading}
                className="w-full gap-2"
              >
                {isAuthLoading ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-spin" />
                    Loading...
                  </>
                ) : canStartReview ? (
                  <>
                    <Sparkles className="w-4 h-4" />
                    {isCreating ? 'Creating...' : 'Start Review'}
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    Sign in to Start Review
                  </>
                )}
              </Button>
              {!canStartReview && !isAuthLoading && (
                <p className="text-xs text-center text-muted-foreground">
                  Create a free account to run your systematic review
                </p>
              )}
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

      {/* Example prompts for inclusion/exclusion stages */}
      {(chat.stage === 'inclusion' || chat.stage === 'exclusion') && (
        <div className="px-4 pb-2">
          <p className="text-xs text-muted-foreground mb-2">Try an example:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS[chat.stage]?.map((prompt, index) => (
              <button
                key={index}
                onClick={() => handleUserMessage(prompt)}
                className="
                  px-3 py-1.5 text-xs
                  bg-secondary/50 hover:bg-secondary
                  border border-border hover:border-foreground/20
                  rounded-full
                  text-muted-foreground hover:text-foreground
                  transition-colors
                "
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

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
