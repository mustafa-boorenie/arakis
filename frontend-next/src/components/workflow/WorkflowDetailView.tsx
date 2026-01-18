'use client';

import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  Search,
  FileText,
  BarChart3,
  PenTool,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Database,
} from 'lucide-react';

// Stage configuration with icons and labels
const STAGES = [
  { key: 'searching', label: 'Searching databases', icon: Search },
  { key: 'screening', label: 'Screening papers', icon: FileText },
  { key: 'analyzing', label: 'Analyzing data', icon: BarChart3 },
  { key: 'writing', label: 'Writing manuscript', icon: PenTool },
  { key: 'finalizing', label: 'Finalizing', icon: CheckCircle2 },
] as const;

// Calculate progress percentage based on stage
function getProgressPercentage(stage: string | null, status: string): number {
  if (status === 'completed') return 100;
  if (status === 'failed') return 0;
  if (!stage) return 0;

  const stageIndex = STAGES.findIndex((s) => s.key === stage);
  if (stageIndex === -1) return 0;

  // Each stage is ~20% of progress
  return Math.min(95, (stageIndex + 1) * 20);
}

// Get estimated time remaining based on stage
function getEstimatedTime(stage: string | null): string | null {
  if (!stage) return null;
  const times: Record<string, string> = {
    searching: '~2-5 mins',
    screening: '~5-15 mins',
    analyzing: '~3-5 mins',
    writing: '~4-6 mins',
    finalizing: '~1 min',
  };
  return times[stage] || null;
}

export function WorkflowDetailView() {
  const workflow = useStore((state) => state.workflow.current);
  const { loadWorkflow } = useWorkflow();

  // Polling is handled by useWorkflow hook - no need to duplicate here

  if (!workflow) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        No workflow selected
      </div>
    );
  }

  const progress = getProgressPercentage(workflow.current_stage, workflow.status);
  const estimatedTime = getEstimatedTime(workflow.current_stage);
  const isRunning = workflow.status === 'running' || workflow.status === 'pending';
  const isCompleted = workflow.status === 'completed';
  const isFailed = workflow.status === 'failed';

  // Handle viewing the completed manuscript
  const handleViewManuscript = async () => {
    if (workflow.status === 'completed') {
      try {
        await loadWorkflow(workflow.id);
      } catch (error) {
        console.error('Failed to load manuscript:', error);
      }
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge
              variant={
                isCompleted ? 'default' : isFailed ? 'destructive' : 'secondary'
              }
              className="capitalize"
            >
              {workflow.status}
            </Badge>
            {estimatedTime && isRunning && (
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {estimatedTime}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-semibold">{workflow.research_question}</h1>
        </div>

        {/* Review Configuration Card */}
        <Card className="p-4 space-y-3">
          <h2 className="font-medium text-sm text-muted-foreground">Review Configuration</h2>
          <div className="grid gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">Inclusion Criteria:</span>
              <p className="mt-0.5">{workflow.inclusion_criteria || 'Not specified'}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Exclusion Criteria:</span>
              <p className="mt-0.5">{workflow.exclusion_criteria || 'Not specified'}</p>
            </div>
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Databases:</span>
              <span>{workflow.databases?.join(', ') || 'pubmed'}</span>
            </div>
          </div>
        </Card>

        {/* Progress Section - Only show when running */}
        {isRunning && (
          <Card className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-medium">Progress</h2>
              <span className="text-sm font-medium">{progress}%</span>
            </div>

            {/* Progress bar */}
            <Progress value={progress} className="h-2" />

            {/* Stages */}
            <div className="space-y-2">
              {STAGES.map((stage) => {
                const StageIcon = stage.icon;
                const currentStageIndex = STAGES.findIndex(
                  (s) => s.key === workflow.current_stage
                );
                const stageIndex = STAGES.findIndex((s) => s.key === stage.key);
                const isActive = stage.key === workflow.current_stage;
                const isComplete = stageIndex < currentStageIndex;
                const isPending = stageIndex > currentStageIndex;

                return (
                  <div
                    key={stage.key}
                    className={`
                      flex items-center gap-3 p-2 rounded-lg transition-colors
                      ${isActive ? 'bg-primary/5' : ''}
                    `}
                  >
                    <div
                      className={`
                        w-8 h-8 rounded-full flex items-center justify-center
                        ${isComplete ? 'bg-green-100 text-green-600' : ''}
                        ${isActive ? 'bg-primary/10 text-primary' : ''}
                        ${isPending ? 'bg-muted text-muted-foreground' : ''}
                      `}
                    >
                      {isActive ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : isComplete ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : (
                        <StageIcon className="w-4 h-4" />
                      )}
                    </div>
                    <span
                      className={`
                        text-sm flex-1
                        ${isActive ? 'font-medium' : ''}
                        ${isPending ? 'text-muted-foreground' : ''}
                      `}
                    >
                      {stage.label}
                    </span>
                    {isActive && (
                      <Badge variant="outline" className="text-xs">
                        In Progress
                      </Badge>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Error Message - Only show when failed */}
        {isFailed && workflow.error_message && (
          <Card className="p-4 border-destructive/50 bg-destructive/5">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="font-medium text-destructive">Review Failed</h3>
                <p className="text-sm text-muted-foreground">
                  {workflow.error_message}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Stats Card */}
        <Card className="p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-3xl font-bold">{workflow.papers_found}</p>
              <p className="text-sm text-muted-foreground">Found</p>
            </div>
            <div>
              <p className="text-3xl font-bold">{workflow.papers_screened}</p>
              <p className="text-sm text-muted-foreground">Screened</p>
            </div>
            <div>
              <p className="text-3xl font-bold">{workflow.papers_included}</p>
              <p className="text-sm text-muted-foreground">Included</p>
            </div>
          </div>
        </Card>

        {/* Cost info */}
        {workflow.total_cost > 0 && (
          <p className="text-sm text-muted-foreground text-center">
            Estimated cost: ${workflow.total_cost.toFixed(2)}
          </p>
        )}

        {/* Action Button for completed workflows */}
        {isCompleted && (
          <Button onClick={handleViewManuscript} className="w-full" size="lg">
            <FileText className="w-4 h-4 mr-2" />
            View Manuscript
          </Button>
        )}
      </div>
    </div>
  );
}
