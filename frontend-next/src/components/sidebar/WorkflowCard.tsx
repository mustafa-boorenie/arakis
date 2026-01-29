'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { WorkflowResponse } from '@/types';
import {
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  FileText,
  Archive,
  ArchiveRestore,
} from 'lucide-react';

interface WorkflowCardProps {
  workflow: WorkflowResponse;
  isActive?: boolean;
  isArchived?: boolean;
  onClick: () => void;
  onDelete: () => void;
  onArchive: () => void;
}

const STATUS_CONFIG: Record<
  string,
  {
    icon: typeof Clock;
    label: string;
    variant: 'default' | 'secondary' | 'destructive';
    animate?: boolean;
  }
> = {
  pending: {
    icon: Clock,
    label: 'Pending',
    variant: 'secondary',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    variant: 'default',
    animate: true,
  },
  completed: {
    icon: CheckCircle,
    label: 'Completed',
    variant: 'default',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    variant: 'destructive',
  },
};

export function WorkflowCard({
  workflow,
  isActive,
  isArchived,
  onClick,
  onDelete,
  onArchive,
}: WorkflowCardProps) {
  const status = STATUS_CONFIG[workflow.status];
  const StatusIcon = status.icon;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const truncateQuestion = (question: string, maxLength = 60) => {
    if (question.length <= maxLength) return question;
    return question.substring(0, maxLength) + '...';
  };

  return (
    <Card
      className={cn(
        'p-3 cursor-pointer transition-all hover:shadow-md group',
        isActive ? 'border-primary bg-primary/5' : 'hover:border-primary/50',
        isArchived && 'opacity-60 bg-muted/30'
      )}
      onClick={onClick}
    >
      <div className="space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <p className="text-sm font-medium truncate">
              {truncateQuestion(workflow.research_question)}
            </p>
          </div>
          <Badge variant={status.variant} className="flex-shrink-0 gap-1">
            <StatusIcon
              className={cn('w-3 h-3', status.animate && 'animate-spin')}
            />
            {status.label}
          </Badge>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>{workflow.papers_found} papers</span>
          <span>{workflow.papers_included} included</span>
          <span>${workflow.total_cost.toFixed(2)}</span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground">
              {formatDate(workflow.created_at)}
            </span>
            {isArchived && (
              <Badge variant="outline" className="text-[10px] h-4 px-1">
                Archived
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onArchive();
              }}
              title={isArchived ? 'Unarchive' : 'Archive'}
            >
              {isArchived ? (
                <ArchiveRestore className="w-3 h-3 text-muted-foreground hover:text-primary" />
              ) : (
                <Archive className="w-3 h-3 text-muted-foreground hover:text-primary" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              title="Delete"
            >
              <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
