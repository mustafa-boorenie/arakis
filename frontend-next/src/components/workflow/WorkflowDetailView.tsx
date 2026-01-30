'use client';

import { useState } from 'react';
import { useStore } from '@/store';
import { useWorkflow } from '@/hooks';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { WORKFLOW_STAGES, StageCheckpoint } from '@/types/workflow';
import { LiveActivityFeed } from './LiveActivityFeed';
import { ProgressStats } from './ProgressStats';
import { EducationalTips } from './EducationalTips';
import { useWorkflowNotifications } from '@/hooks/useNotifications';
import {
  Search,
  FileText,
  Download,
  ClipboardList,
  Shield,
  BarChart3,
  GitBranch,
  Table,
  BookOpen,
  FileCode,
  FileBarChart,
  MessageSquare,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Database,
  RefreshCw,
  AlertTriangle,
  Image as ImageIcon,
} from 'lucide-react';

// Stage configuration with icons
const STAGE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  search: Search,
  screen: FileText,
  pdf_fetch: Download,
  extract: ClipboardList,
  rob: Shield,
  analysis: BarChart3,
  prisma: GitBranch,
  tables: Table,
  introduction: BookOpen,
  methods: FileCode,
  results: FileBarChart,
  discussion: MessageSquare,
};

// Calculate progress percentage based on stages
function getProgressPercentage(
  stages: StageCheckpoint[] | undefined,
  status: string
): number {
  if (status === 'completed') return 100;
  if (status === 'failed') return 0;
  if (!stages || stages.length === 0) return 0;

  const completedStages = stages.filter(
    (s) => s.status === 'completed' || s.status === 'skipped'
  ).length;
  const totalStages = WORKFLOW_STAGES.length;

  return Math.round((completedStages / totalStages) * 100);
}

// Find current active stage
function getCurrentStage(stages: StageCheckpoint[] | undefined): string | null {
  if (!stages) return null;
  const inProgress = stages.find((s) => s.status === 'in_progress');
  return inProgress?.stage || null;
}

export function WorkflowDetailView() {
  const workflow = useStore((state) => state.workflow.current);
  const { loadWorkflow, resumeWorkflow, rerunStage } = useWorkflow();
  const [showTips, setShowTips] = useState(true);

  // Enable browser notifications for workflow completion
  useWorkflowNotifications(
    workflow?.id || null,
    workflow?.status || null,
    workflow?.research_question || null
  );

  if (!workflow) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        No workflow selected
      </div>
    );
  }

  const progress = getProgressPercentage(workflow.stages, workflow.status);
  const currentStage = getCurrentStage(workflow.stages);
  const isRunning = workflow.status === 'running' || workflow.status === 'pending';
  const isCompleted = workflow.status === 'completed';
  const isFailed = workflow.status === 'failed';
  const needsReview = workflow.status === 'needs_review';

  // Get the current stage's progress data
  const currentStageCheckpoint = workflow.stages?.find((s) => s.status === 'in_progress');
  const currentProgress = currentStageCheckpoint?.progress;

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

  // Handle resuming workflow
  const handleResume = async () => {
    try {
      await resumeWorkflow(workflow.id);
    } catch (error) {
      console.error('Failed to resume workflow:', error);
    }
  };

  // Handle retrying a failed stage
  const handleRetryStage = async (stage: string) => {
    try {
      await rerunStage(workflow.id, stage);
    } catch (error) {
      console.error('Failed to retry stage:', error);
    }
  };

  // Get stage status from checkpoints
  const getStageStatus = (stageKey: string): 'completed' | 'in_progress' | 'pending' | 'failed' | 'skipped' => {
    const checkpoint = workflow.stages?.find((s) => s.stage === stageKey);
    if (!checkpoint) return 'pending';
    return checkpoint.status;
  };

  // Get failed stage from checkpoints
  const getFailedStage = (): StageCheckpoint | null => {
    return workflow.stages?.find((s) => s.status === 'failed') || null;
  };

  const failedStage = getFailedStage();

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge
              variant={
                isCompleted
                  ? 'default'
                  : isFailed
                    ? 'destructive'
                    : needsReview
                      ? 'secondary'
                      : 'secondary'
              }
              className={`capitalize ${
                isRunning
                  ? 'bg-purple-100 text-purple-700 hover:bg-purple-100'
                  : isCompleted
                    ? 'bg-green-100 text-green-700 hover:bg-green-100'
                    : needsReview
                      ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-100'
                      : ''
              }`}
            >
              {workflow.status === 'needs_review' ? 'Needs Review' : workflow.status}
            </Badge>
            {isRunning && currentStage && (
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Processing...
              </span>
            )}
          </div>
          <h1 className="text-2xl font-semibold">{workflow.research_question}</h1>
        </div>

        {/* User Action Required Alert */}
        {needsReview && workflow.action_required && (
          <Card className="p-4 border-yellow-300 bg-yellow-50">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-2 flex-1">
                <h3 className="font-medium text-yellow-800">Action Required</h3>
                <p className="text-sm text-yellow-700">{workflow.action_required}</p>
                <Button
                  onClick={handleResume}
                  className="bg-yellow-600 hover:bg-yellow-700"
                  size="sm"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Resume Workflow
                </Button>
              </div>
            </div>
          </Card>
        )}

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

        {/* Progress Section - Show when running or has stages */}
        {(isRunning || (workflow.stages && workflow.stages.length > 0)) && (
          <Card className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-medium">Progress</h2>
              <span className="text-sm font-medium">{progress}%</span>
            </div>

            {/* Progress bar */}
            <Progress value={progress} className="h-2" />

            {/* 12 Stages */}
            <div className="space-y-1.5">
              {WORKFLOW_STAGES.map((stage) => {
                const StageIcon = STAGE_ICONS[stage.key] || FileText;
                const status = getStageStatus(stage.key);
                const isActive = status === 'in_progress';
                const isComplete = status === 'completed';
                const isSkipped = status === 'skipped';
                const isStageFailed = status === 'failed';
                const isPending = status === 'pending';
                const checkpoint = workflow.stages?.find((s) => s.stage === stage.key);

                return (
                  <div
                    key={stage.key}
                    className={`
                      flex items-center gap-3 p-2 rounded-lg transition-colors
                      ${isActive ? 'bg-purple-50' : ''}
                      ${isStageFailed ? 'bg-red-50' : ''}
                    `}
                  >
                    <div
                      className={`
                        w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0
                        ${isComplete ? 'bg-green-100 text-green-600' : ''}
                        ${isActive ? 'bg-purple-100 text-purple-600' : ''}
                        ${isSkipped ? 'bg-gray-100 text-gray-400' : ''}
                        ${isStageFailed ? 'bg-red-100 text-red-600' : ''}
                        ${isPending ? 'bg-muted text-muted-foreground' : ''}
                      `}
                    >
                      {isActive ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : isComplete ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      ) : isStageFailed ? (
                        <AlertCircle className="w-3.5 h-3.5" />
                      ) : (
                        <StageIcon className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span
                        className={`
                          text-sm block truncate
                          ${isActive ? 'font-medium text-purple-700' : ''}
                          ${isStageFailed ? 'font-medium text-red-700' : ''}
                          ${isSkipped ? 'text-gray-400' : ''}
                          ${isPending ? 'text-muted-foreground' : ''}
                        `}
                      >
                        {stage.label}
                      </span>
                      {isActive && (
                        <span className="text-xs text-muted-foreground">{stage.description}</span>
                      )}
                    </div>
                    {isActive && (
                      <Badge
                        variant="outline"
                        className="text-xs border-purple-200 bg-purple-50 text-purple-700 flex-shrink-0"
                      >
                        In Progress
                      </Badge>
                    )}
                    {isStageFailed && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs h-7 border-red-200 text-red-600 hover:bg-red-50"
                        onClick={() => handleRetryStage(stage.key)}
                      >
                        <RefreshCw className="w-3 h-3 mr-1" />
                        Retry
                      </Button>
                    )}
                    {checkpoint?.retry_count && checkpoint.retry_count > 0 && (
                      <span className="text-xs text-muted-foreground">
                        (retry {checkpoint.retry_count})
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Live Progress Stats - Show when running and has progress data */}
        {isRunning && currentStage && currentProgress && (
          <ProgressStats
            progress={currentProgress}
            stage={currentStage}
            papersFound={workflow.papers_found}
            papersScreened={workflow.papers_screened}
            papersIncluded={workflow.papers_included}
          />
        )}

        {/* Live Activity Feed - Show when running and has recent decisions */}
        {isRunning && currentStage && currentProgress && (
          <LiveActivityFeed
            progress={currentProgress}
            stage={currentStage}
          />
        )}

        {/* Educational Tips - Show when running */}
        {isRunning && currentStage && showTips && (
          <EducationalTips
            stage={currentStage}
            onDismiss={() => setShowTips(false)}
          />
        )}

        {/* Error Message - Only show when failed */}
        {isFailed && (failedStage?.error_message || workflow.error_message) && (
          <Card className="p-4 border-destructive/50 bg-destructive/5">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div className="space-y-2 flex-1">
                <h3 className="font-medium text-destructive">
                  {failedStage ? `Stage Failed: ${failedStage.stage}` : 'Review Failed'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {failedStage?.error_message || workflow.error_message}
                </p>
                {failedStage && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-red-200 text-red-600 hover:bg-red-50"
                    onClick={() => handleRetryStage(failedStage.stage)}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry Stage
                  </Button>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Figure Previews */}
        {isCompleted && (workflow.forest_plot_url || workflow.funnel_plot_url || workflow.prisma_url) && (
          <Card className="p-4 space-y-3">
            <h2 className="font-medium text-sm text-muted-foreground">Generated Figures</h2>
            <div className="grid grid-cols-3 gap-3">
              {workflow.prisma_url && (
                <a
                  href={workflow.prisma_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg border hover:border-purple-300 hover:bg-purple-50 transition-colors"
                >
                  <ImageIcon className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-center text-muted-foreground">PRISMA Flow</p>
                </a>
              )}
              {workflow.forest_plot_url && (
                <a
                  href={workflow.forest_plot_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg border hover:border-purple-300 hover:bg-purple-50 transition-colors"
                >
                  <BarChart3 className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-center text-muted-foreground">Forest Plot</p>
                </a>
              )}
              {workflow.funnel_plot_url && (
                <a
                  href={workflow.funnel_plot_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg border hover:border-purple-300 hover:bg-purple-50 transition-colors"
                >
                  <GitBranch className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-center text-muted-foreground">Funnel Plot</p>
                </a>
              )}
            </div>
          </Card>
        )}

        {/* Meta-analysis feasibility badge */}
        {isCompleted && workflow.meta_analysis_feasible !== null && (
          <div className="flex justify-center">
            <Badge
              variant="outline"
              className={
                workflow.meta_analysis_feasible
                  ? 'border-green-200 bg-green-50 text-green-700'
                  : 'border-gray-200 bg-gray-50 text-gray-600'
              }
            >
              {workflow.meta_analysis_feasible
                ? 'Meta-analysis performed'
                : 'Narrative synthesis (meta-analysis not feasible)'}
            </Badge>
          </div>
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
          <Button
            onClick={handleViewManuscript}
            className="w-full bg-purple-600 hover:bg-purple-700"
            size="lg"
          >
            <FileText className="w-4 h-4 mr-2" />
            View Manuscript
          </Button>
        )}
      </div>
    </div>
  );
}
