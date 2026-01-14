'use client';

import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types';
import { Bot, User } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isAssistant = message.role === 'assistant';

  return (
    <div
      className={cn(
        'flex gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300',
        isAssistant ? 'flex-row' : 'flex-row-reverse'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isAssistant ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {isAssistant ? (
          <Bot className="w-5 h-5" />
        ) : (
          <User className="w-5 h-5" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3',
          isAssistant
            ? 'bg-muted text-foreground rounded-tl-sm'
            : 'bg-primary text-primary-foreground rounded-tr-sm'
        )}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        {message.metadata?.isLoading && (
          <div className="flex gap-1 mt-2">
            <span className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-2 h-2 bg-current rounded-full animate-bounce" />
          </div>
        )}
      </div>
    </div>
  );
}
