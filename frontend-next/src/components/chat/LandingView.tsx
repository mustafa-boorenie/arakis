'use client';

import { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  'Effect of aspirin on mortality in sepsis patients',
  'Efficacy of cognitive behavioral therapy for depression',
  'Impact of telemedicine on diabetes management outcomes',
  'Effectiveness of early mobilization in ICU patients',
];

interface LandingViewProps {
  onSubmit: (message: string) => void;
}

export function LandingView({ onSubmit }: LandingViewProps) {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!value.trim()) return;
    onSubmit(value.trim());
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [value]);

  // Focus input on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      {/* Centered Headline */}
      <h1 className="text-3xl md:text-4xl font-medium text-foreground mb-8 text-center">
        What would you like to research?
      </h1>

      {/* Pill-shaped Input Container */}
      <div
        className={`
          w-full max-w-2xl
          bg-secondary/50 dark:bg-secondary
          rounded-3xl
          border border-border
          transition-all duration-200
          ${isFocused ? 'ring-2 ring-ring/20 border-foreground/20' : ''}
        `}
      >
        <div className="flex items-center gap-2 px-4 py-3">
          {/* Text Input */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Enter your research question..."
            className="
              flex-1 bg-transparent border-none outline-none resize-none
              text-base text-foreground placeholder:text-muted-foreground
              py-1 min-h-[28px] max-h-[120px]
            "
            rows={1}
          />

          {/* Submit Button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!value.trim()}
            className={`
              flex-shrink-0 p-2 rounded-full transition-colors
              ${value.trim()
                ? 'bg-foreground text-background hover:bg-foreground/90'
                : 'bg-muted text-muted-foreground'
              }
            `}
            title="Send"
          >
            <ArrowUp className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Example Prompts */}
      <div className="mt-6 w-full max-w-2xl">
        <p className="text-xs text-muted-foreground text-center mb-3">
          Try an example
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {EXAMPLE_PROMPTS.map((prompt, index) => (
            <button
              key={index}
              onClick={() => onSubmit(prompt)}
              className="
                px-3 py-2 text-sm
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
    </div>
  );
}
