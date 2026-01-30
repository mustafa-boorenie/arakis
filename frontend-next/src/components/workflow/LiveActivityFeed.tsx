'use client';

import { useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { StageProgress, RecentDecision } from '@/types/workflow';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  FileText,
  Lightbulb,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface LiveActivityFeedProps {
  progress: StageProgress | null | undefined;
  stage: string;
  className?: string;
}

// Decision badge styling based on decision type
const getDecisionBadge = (decision: string, isConflict: boolean) => {
  if (isConflict) {
    return {
      variant: 'outline' as const,
      className: 'border-yellow-400 bg-yellow-50 text-yellow-700',
      icon: AlertTriangle,
    };
  }

  switch (decision.toUpperCase()) {
    case 'INCLUDE':
      return {
        variant: 'outline' as const,
        className: 'border-green-400 bg-green-50 text-green-700',
        icon: CheckCircle2,
      };
    case 'EXCLUDE':
      return {
        variant: 'outline' as const,
        className: 'border-red-400 bg-red-50 text-red-700',
        icon: XCircle,
      };
    case 'MAYBE':
      return {
        variant: 'outline' as const,
        className: 'border-blue-400 bg-blue-50 text-blue-700',
        icon: HelpCircle,
      };
    default:
      return {
        variant: 'outline' as const,
        className: '',
        icon: FileText,
      };
  }
};

// Format confidence as percentage
const formatConfidence = (confidence: number) => {
  return `${Math.round(confidence * 100)}%`;
};

// Activity item for screening decisions
function ScreeningActivityItem({ event }: { event: RecentDecision | Record<string, unknown> }) {
  const decision = event as RecentDecision;
  const badge = getDecisionBadge(decision.decision || '', decision.is_conflict || false);
  const Icon = badge.icon;

  return (
    <div className="p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          decision.is_conflict ? 'bg-yellow-100' :
          (decision.decision || '').toUpperCase() === 'INCLUDE' ? 'bg-green-100' :
          (decision.decision || '').toUpperCase() === 'EXCLUDE' ? 'bg-red-100' : 'bg-blue-100'
        }`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={badge.className}>
              {decision.is_conflict ? 'CONFLICT' : decision.decision}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {formatConfidence(decision.confidence || 0)} confidence
            </span>
          </div>
          <p className="text-sm font-medium truncate" title={decision.title}>
            {decision.title || 'Untitled paper'}
          </p>
          {decision.reason && (
            <p className="text-xs text-muted-foreground line-clamp-2">
              {decision.reason}
            </p>
          )}
          {(decision.matched_inclusion?.length > 0 || decision.matched_exclusion?.length > 0) && (
            <div className="flex flex-wrap gap-1 mt-1">
              {decision.matched_inclusion?.map((criterion, i) => (
                <Badge key={`inc-${i}`} variant="outline" className="text-[10px] px-1.5 py-0 h-5 bg-green-50 border-green-200 text-green-700">
                  {criterion}
                </Badge>
              ))}
              {decision.matched_exclusion?.map((criterion, i) => (
                <Badge key={`exc-${i}`} variant="outline" className="text-[10px] px-1.5 py-0 h-5 bg-red-50 border-red-200 text-red-700">
                  {criterion}
                </Badge>
              ))}
            </div>
          )}
          {decision.timestamp && (
            <p className="text-[10px] text-muted-foreground mt-1">
              {formatDistanceToNow(new Date(decision.timestamp), { addSuffix: true })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// Generic activity item for other events
function GenericActivityItem({ event }: { event: Record<string, unknown> }) {
  const itemData = event.item_data as Record<string, unknown> | undefined;
  const itemTitle = itemData?.title as string | undefined;

  return (
    <div className="p-3 rounded-lg border bg-card">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-muted">
          <FileText className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm">
            {(event.event_type as string) || 'Processing'}
          </p>
          {itemTitle && (
            <p className="text-xs text-muted-foreground truncate">
              {itemTitle}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// Thought process display
function ThoughtProcess({ thought }: { thought: string }) {
  return (
    <div className="p-3 rounded-lg border border-purple-200 bg-purple-50">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-100">
          <Lightbulb className="w-4 h-4 text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-purple-700 mb-1">AI Reasoning</p>
          <p className="text-sm text-purple-900">{thought}</p>
        </div>
      </div>
    </div>
  );
}

export function LiveActivityFeed({ progress, stage, className = '' }: LiveActivityFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [progress?.recent_decisions?.length]);

  if (!progress) {
    return null;
  }

  const recentEvents = progress.recent_decisions || [];
  const hasEvents = recentEvents.length > 0;
  const thoughtProcess = progress.thought_process;

  // Determine if this is a screening stage
  const isScreeningStage = stage === 'screen';

  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-sm">Live Activity</h3>
        {hasEvents && (
          <span className="text-xs text-muted-foreground">
            Last {recentEvents.length} events
          </span>
        )}
      </div>

      {/* Thought process banner */}
      {thoughtProcess && (
        <div className="mb-3">
          <ThoughtProcess thought={thoughtProcess} />
        </div>
      )}

      {/* Activity feed */}
      {hasEvents ? (
        <ScrollArea className="h-[300px]" ref={scrollRef as React.RefObject<HTMLDivElement>}>
          <div className="space-y-2 pr-4">
            {recentEvents.map((event, index) => (
              <div key={index}>
                {isScreeningStage && (event as RecentDecision).decision ? (
                  <ScreeningActivityItem event={event} />
                ) : (
                  <GenericActivityItem event={event as Record<string, unknown>} />
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      ) : (
        <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
          Waiting for activity...
        </div>
      )}
    </Card>
  );
}
