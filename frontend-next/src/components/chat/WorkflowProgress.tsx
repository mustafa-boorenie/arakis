'use client';

import { useStore } from '@/store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import {
  Search,
  Filter,
  FileText,
  CheckCircle,
  Loader2,
  AlertCircle,
} from 'lucide-react';

const STAGES = [
  { id: 'searching', label: 'Searching databases', icon: Search },
  { id: 'screening', label: 'Screening papers', icon: Filter },
  { id: 'writing', label: 'Writing manuscript', icon: FileText },
  { id: 'complete', label: 'Complete', icon: CheckCircle },
];

export function WorkflowProgress() {
  const { workflow } = useStore();
  const current = workflow.current;

  if (!current) return null;

  // Determine current stage based on workflow data
  const getCurrentStage = () => {
    if (current.status === 'completed') return 'complete';
    if (current.status === 'failed') return 'failed';
    if (current.papers_screened > 0) return 'writing';
    if (current.papers_found > 0) return 'screening';
    return 'searching';
  };

  const currentStage = getCurrentStage();
  const stageIndex = STAGES.findIndex((s) => s.id === currentStage);
  const progress =
    currentStage === 'complete'
      ? 100
      : currentStage === 'failed'
        ? 0
        : ((stageIndex + 1) / STAGES.length) * 100;

  return (
    <Card className="p-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      <div className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Stages */}
        <div className="space-y-2">
          {STAGES.map((stage, index) => {
            const Icon = stage.icon;
            const isActive = stage.id === currentStage;
            const isComplete =
              currentStage === 'complete' || index < stageIndex;
            const isFailed = currentStage === 'failed' && stage.id === currentStage;

            return (
              <div
                key={stage.id}
                className={cn(
                  'flex items-center gap-3 p-2 rounded-lg transition-colors',
                  isActive && 'bg-primary/10',
                  isComplete && 'text-primary'
                )}
              >
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center',
                    isComplete
                      ? 'bg-primary text-primary-foreground'
                      : isActive
                        ? 'bg-primary/20 text-primary'
                        : 'bg-muted text-muted-foreground'
                  )}
                >
                  {isActive && !isFailed ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isFailed ? (
                    <AlertCircle className="w-4 h-4" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>
                <span
                  className={cn(
                    'text-sm',
                    isActive ? 'font-medium' : 'text-muted-foreground'
                  )}
                >
                  {stage.label}
                </span>
                {isActive && !isFailed && (
                  <Badge variant="secondary" className="ml-auto">
                    In Progress
                  </Badge>
                )}
              </div>
            );
          })}
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
      </div>
    </Card>
  );
}
