'use client';

import { useStore } from '@/store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import {
  Search,
  Filter,
  BarChart3,
  FileText,
  CheckCircle,
  Loader2,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react';

const STAGES = [
  { id: 'searching', label: 'Searching databases', icon: Search },
  { id: 'screening', label: 'Screening papers', icon: Filter },
  { id: 'analyzing', label: 'Analyzing data', icon: BarChart3 },
  { id: 'writing', label: 'Writing manuscript', icon: FileText },
  { id: 'finalizing', label: 'Finalizing', icon: CheckCircle },
  { id: 'completed', label: 'Complete', icon: CheckCircle },
];

const STAGE_DESCRIPTIONS: Record<string, string> = {
  searching: 'Querying PubMed, OpenAlex, and other databases...',
  screening: 'AI is reviewing titles and abstracts...',
  analyzing: 'Generating PRISMA diagram and statistics...',
  writing: 'Writing introduction, methods, results, discussion...',
  finalizing: 'Assembling manuscript and references...',
  completed: 'Your systematic review is ready!',
};

export function WorkflowProgress() {
  const { workflow } = useStore();
  const current = workflow.current;

  if (!current) return null;

  // Use current_stage from backend, fall back to derived stage
  const getCurrentStage = () => {
    if (current.status === 'completed') return 'completed';
    if (current.status === 'failed') return 'failed';
    if (current.status === 'needs_review') return 'needs_review';

    // Use backend-provided current_stage if available
    if (current.current_stage) {
      return current.current_stage;
    }

    // Fall back to derived stage
    if (current.papers_screened > 0 && current.papers_included > 0) return 'writing';
    if (current.papers_found > 0) return 'screening';
    return 'searching';
  };

  const currentStage = getCurrentStage();
  const stageIndex = STAGES.findIndex((s) => s.id === currentStage);
  const progress =
    currentStage === 'completed'
      ? 100
      : currentStage === 'failed' || currentStage === 'needs_review'
        ? Math.max(((stageIndex + 0.5) / STAGES.length) * 100, 10)
        : ((stageIndex + 0.5) / STAGES.length) * 100;

  const isNeedsReview = current.status === 'needs_review';
  const isFailed = current.status === 'failed';

  return (
    <Card className="p-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      <div className="space-y-4">
        {/* Status banner for needs_review */}
        {isNeedsReview && (
          <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            <div>
              <p className="font-medium text-sm">Review Required</p>
              <p className="text-xs text-muted-foreground">
                Some papers need your input to continue.
              </p>
            </div>
          </div>
        )}

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              {currentStage === 'completed'
                ? 'Complete!'
                : STAGE_DESCRIPTIONS[currentStage] || 'Processing...'}
            </span>
            <span className="font-medium">{Math.round(progress)}%</span>
          </div>
          <Progress
            value={progress}
            className={cn(
              'h-2',
              isFailed && '[&>div]:bg-destructive',
              isNeedsReview && '[&>div]:bg-yellow-500'
            )}
          />
        </div>

        {/* Stages */}
        <div className="space-y-2">
          {STAGES.filter((s) => s.id !== 'completed' || currentStage === 'completed').map(
            (stage, index) => {
              const Icon = stage.icon;
              const isActive = stage.id === currentStage;
              const isComplete = currentStage === 'completed' || index < stageIndex;

              return (
                <div
                  key={stage.id}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg transition-colors',
                    isActive && !isFailed && 'bg-primary/10',
                    isActive && isFailed && 'bg-destructive/10',
                    isComplete && 'text-primary'
                  )}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center',
                      isComplete
                        ? 'bg-primary text-primary-foreground'
                        : isActive && !isFailed
                          ? 'bg-primary/20 text-primary'
                          : isActive && isFailed
                            ? 'bg-destructive/20 text-destructive'
                            : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {isActive && !isFailed && !isNeedsReview ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isFailed && isActive ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : isNeedsReview && isActive ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-sm flex-1',
                      isActive ? 'font-medium' : 'text-muted-foreground'
                    )}
                  >
                    {stage.label}
                  </span>
                  {isActive && !isFailed && !isNeedsReview && (
                    <Badge variant="secondary" className="ml-auto">
                      In Progress
                    </Badge>
                  )}
                  {isActive && isNeedsReview && (
                    <Badge variant="outline" className="ml-auto border-yellow-500 text-yellow-600">
                      Needs Review
                    </Badge>
                  )}
                  {isComplete && !isActive && (
                    <CheckCircle className="w-4 h-4 text-primary ml-auto" />
                  )}
                </div>
              );
            }
          )}
        </div>

        {/* Stats */}
        {(current.papers_found > 0 || current.papers_included > 0) && (
          <div className="grid grid-cols-3 gap-2 pt-2 border-t">
            <div className="text-center">
              <p className="text-lg font-semibold">{current.papers_found}</p>
              <p className="text-xs text-muted-foreground">Found</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-semibold">{current.papers_screened}</p>
              <p className="text-xs text-muted-foreground">Screened</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-semibold">{current.papers_included}</p>
              <p className="text-xs text-muted-foreground">Included</p>
            </div>
          </div>
        )}

        {/* Cost */}
        {current.total_cost > 0 && (
          <div className="text-center pt-2 border-t">
            <p className="text-sm text-muted-foreground">
              Estimated cost:{' '}
              <span className="font-medium">${current.total_cost.toFixed(2)}</span>
            </p>
          </div>
        )}

        {/* Error message */}
        {isFailed && current.error_message && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{current.error_message}</p>
          </div>
        )}
      </div>
    </Card>
  );
}
