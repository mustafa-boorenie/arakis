'use client';

import { useState, useRef, useEffect } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { Button } from '@/components/ui/button';
import {
  Bell,
  HelpCircle,
  Send,
} from 'lucide-react';

const EXAMPLE_PROMPTS = [
  'Effect of aspirin on mortality in sepsis patients',
  'Efficacy of cognitive behavioral therapy for depression',
  'Impact of telemedicine on diabetes management outcomes',
];

export function Dashboard() {
  const [researchQuestion, setResearchQuestion] = useState('');
  const [, setIsExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const user = useStore((state) => state.auth.user);
  const { addMessage, setChatStage, setLayoutMode, updateFormData } = useStore();
  const { isCreating } = useWorkflow();

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [researchQuestion]);

  const handleStartResearch = async () => {
    if (!researchQuestion.trim()) return;

    // Update form data with research question
    updateFormData({ research_question: researchQuestion.trim() });

    // Add messages to start chat flow
    addMessage({
      role: 'user',
      content: researchQuestion.trim(),
    });
    addMessage({
      role: 'assistant',
      content: "Great question! Now, what are your inclusion criteria? Enter them as comma-separated values (e.g., 'Adult patients, RCTs, English language').",
    });

    // Move to inclusion stage
    setChatStage('inclusion');
    setLayoutMode('chat-fullscreen');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleStartResearch();
    }
  };

  const getUserFirstName = () => {
    if (!user) return 'there';
    if (user.full_name) {
      return user.full_name.split(' ')[0];
    }
    return user.email.split('@')[0];
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-100">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Welcome back, <span className="text-purple-600">{getUserFirstName()}</span>
          </h1>
          <p className="text-sm text-gray-500">
            Continue your latest review or start something new.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Notification Icons */}
          <button className="relative p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
          </button>
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <HelpCircle className="w-5 h-5" />
          </button>

          {/* User Avatar */}
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center text-white text-sm font-medium">
            {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        {/* Tagline */}
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900">
            Condense{' '}
            <span className="text-purple-600 italic">Months</span>
            {' '}into{' '}
            <span className="text-purple-600 italic">Minutes</span>
          </h2>
        </div>

        {/* Research Input Card */}
        <div className="w-full max-w-2xl">
          <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
            {/* Input Area */}
            <div className="p-4">
              <textarea
                ref={textareaRef}
                value={researchQuestion}
                onChange={(e) => setResearchQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsExpanded(true)}
                placeholder="What do you want to research? Type it here..."
                className="w-full resize-none border-none outline-none text-gray-700 placeholder:text-gray-400 text-base min-h-[80px]"
                rows={3}
              />

              {/* Start Research Button */}
              <div className="flex justify-end mt-2">
                <Button
                  onClick={handleStartResearch}
                  disabled={!researchQuestion.trim() || isCreating}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6"
                >
                  {isCreating ? 'Starting...' : 'Start Research'}
                  <Send className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          </div>

          {/* Example Prompts - Outside card, centered */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500 mb-3">Try an example:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLE_PROMPTS.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => setResearchQuestion(prompt)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-200 rounded-full transition-colors shadow-sm"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
