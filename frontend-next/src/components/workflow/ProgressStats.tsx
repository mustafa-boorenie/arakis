'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { StageProgress } from '@/types/workflow';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Clock,
  Download,
  Pen,
} from 'lucide-react';

interface ProgressStatsProps {
  progress: StageProgress | null | undefined;
  stage: string;
  papersFound?: number;
  papersScreened?: number;
  papersIncluded?: number;
  className?: string;
}

// Animated counter component
function AnimatedCounter({ value, duration = 500 }: { value: number; duration?: number }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const start = displayValue;
    const end = value;
    if (start === end) return;

    const increment = (end - start) / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
        setDisplayValue(end);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.round(current));
      }
    }, 16);

    return () => clearInterval(timer);
  }, [value, duration, displayValue]);

  return <span>{displayValue}</span>;
}

// Circular progress ring
function ProgressRing({
  progress,
  size = 60,
  strokeWidth = 4,
  color = 'stroke-purple-500'
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        className="stroke-muted"
        strokeWidth={strokeWidth}
        fill="none"
        r={radius}
        cx={size / 2}
        cy={size / 2}
      />
      <circle
        className={`${color} transition-all duration-500 ease-out`}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        fill="none"
        r={radius}
        cx={size / 2}
        cy={size / 2}
        style={{ strokeDasharray: circumference, strokeDashoffset: offset }}
      />
    </svg>
  );
}

// Mini donut chart for decision distribution
function DecisionDonut({
  included,
  excluded,
  maybe,
  total,
  size = 80
}: {
  included: number;
  excluded: number;
  maybe: number;
  total: number;
  size?: number;
}) {
  if (total === 0) return null;

  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;

  const includedPercent = (included / total) * 100;
  const excludedPercent = (excluded / total) * 100;
  const maybePercent = (maybe / total) * 100;

  // Calculate offsets
  const includedOffset = circumference - (includedPercent / 100) * circumference;
  const excludedOffset = circumference - (excludedPercent / 100) * circumference;
  const maybeOffset = circumference - (maybePercent / 100) * circumference;

  // Cumulative rotations
  const includedRotation = 0;
  const excludedRotation = includedPercent * 3.6;
  const maybeRotation = (includedPercent + excludedPercent) * 3.6;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background */}
        <circle
          className="stroke-muted"
          strokeWidth={strokeWidth}
          fill="none"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Included (green) */}
        {included > 0 && (
          <circle
            className="stroke-green-500"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            fill="none"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: includedOffset,
              transform: `rotate(${includedRotation}deg)`,
              transformOrigin: '50% 50%'
            }}
          />
        )}
        {/* Excluded (red) */}
        {excluded > 0 && (
          <circle
            className="stroke-red-500"
            strokeWidth={strokeWidth}
            fill="none"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: excludedOffset,
              transform: `rotate(${excludedRotation}deg)`,
              transformOrigin: '50% 50%'
            }}
          />
        )}
        {/* Maybe (blue) */}
        {maybe > 0 && (
          <circle
            className="stroke-blue-500"
            strokeWidth={strokeWidth}
            fill="none"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: maybeOffset,
              transform: `rotate(${maybeRotation}deg)`,
              transformOrigin: '50% 50%'
            }}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-bold">{total}</span>
      </div>
    </div>
  );
}

// Estimated time display
function EstimatedTime({ seconds }: { seconds: number }) {
  if (!seconds || seconds <= 0) return null;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Clock className="w-4 h-4" />
      <span>
        ~{minutes > 0 ? `${minutes}m ` : ''}{remainingSeconds}s remaining
      </span>
    </div>
  );
}

export function ProgressStats({
  progress,
  stage,
  papersFound: _papersFound = 0,
  papersScreened: _papersScreened = 0,
  papersIncluded: _papersIncluded = 0,
  className = ''
}: ProgressStatsProps) {
  // These props are available for future use
  void _papersFound;
  void _papersScreened;
  void _papersIncluded;
  const summary = progress?.summary;
  const estimatedSeconds = progress?.estimated_remaining_seconds;

  // Calculate stage-specific progress
  const getStageProgress = () => {
    if (!progress) return 0;

    switch (stage) {
      case 'screen':
        const total = summary?.total || 0;
        const processed = (summary?.included || 0) + (summary?.excluded || 0) + (summary?.maybe || 0);
        return total > 0 ? (processed / total) * 100 : 0;
      case 'pdf_fetch':
        const fetchTotal = summary?.total || 0;
        const fetched = (summary?.fetched || 0) + (summary?.failed || 0);
        return fetchTotal > 0 ? (fetched / fetchTotal) * 100 : 0;
      case 'introduction':
      case 'methods':
      case 'results':
      case 'discussion':
        const subsCompleted = progress.subsections_completed?.length || 0;
        const subsTotal = subsCompleted + (progress.subsections_pending?.length || 0);
        return subsTotal > 0 ? (subsCompleted / subsTotal) * 100 : 0;
      default:
        return 0;
    }
  };

  const stageProgress = getStageProgress();

  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-sm">Progress Statistics</h3>
        {estimatedSeconds && estimatedSeconds > 0 && (
          <EstimatedTime seconds={estimatedSeconds} />
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Stage Progress Ring */}
        <div className="flex flex-col items-center justify-center">
          <ProgressRing progress={stageProgress} size={80} strokeWidth={6} />
          <span className="text-sm font-medium mt-2">
            {Math.round(stageProgress)}% Complete
          </span>
        </div>

        {/* Stage-specific stats */}
        {stage === 'screen' && summary && (
          <div className="flex flex-col items-center justify-center">
            <DecisionDonut
              included={summary.included || 0}
              excluded={summary.excluded || 0}
              maybe={summary.maybe || 0}
              total={summary.total || 0}
            />
            <span className="text-sm text-muted-foreground mt-2">Decisions</span>
          </div>
        )}

        {stage === 'pdf_fetch' && summary && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Download className="w-4 h-4 text-green-500" />
              <span className="text-sm">
                <AnimatedCounter value={summary.fetched || 0} /> fetched
              </span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm">
                <AnimatedCounter value={summary.failed || 0} /> failed
              </span>
            </div>
          </div>
        )}

        {(stage === 'introduction' || stage === 'methods' || stage === 'results' || stage === 'discussion') && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Pen className="w-4 h-4 text-purple-500" />
              <span className="text-sm">
                <AnimatedCounter value={progress?.word_count || 0} /> words
              </span>
            </div>
            {progress?.current_subsection && (
              <div className="text-sm text-muted-foreground">
                Writing: {progress.current_subsection}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Screening detailed stats */}
      {stage === 'screen' && summary && (
        <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            </div>
            <p className="text-lg font-bold text-green-600">
              <AnimatedCounter value={summary.included || 0} />
            </p>
            <p className="text-[10px] text-muted-foreground">Included</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <XCircle className="w-3.5 h-3.5 text-red-500" />
            </div>
            <p className="text-lg font-bold text-red-600">
              <AnimatedCounter value={summary.excluded || 0} />
            </p>
            <p className="text-[10px] text-muted-foreground">Excluded</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <HelpCircle className="w-3.5 h-3.5 text-blue-500" />
            </div>
            <p className="text-lg font-bold text-blue-600">
              <AnimatedCounter value={summary.maybe || 0} />
            </p>
            <p className="text-[10px] text-muted-foreground">Maybe</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" />
            </div>
            <p className="text-lg font-bold text-yellow-600">
              <AnimatedCounter value={summary.conflicts || 0} />
            </p>
            <p className="text-[10px] text-muted-foreground">Conflicts</p>
          </div>
        </div>
      )}
    </Card>
  );
}
