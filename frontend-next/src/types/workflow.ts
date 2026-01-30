// TypeScript types matching backend schemas from:
// src/arakis/api/schemas/workflow.py

export type WorkflowStatus = 'pending' | 'running' | 'needs_review' | 'completed' | 'failed';

// 12 comprehensive workflow stages
export type WorkflowStage =
  | 'search'
  | 'screen'
  | 'pdf_fetch'
  | 'extract'
  | 'rob'
  | 'analysis'
  | 'prisma'
  | 'tables'
  | 'introduction'
  | 'methods'
  | 'results'
  | 'discussion'
  | 'completed';

export type StageStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';

// A recent decision from the screening/processing activity feed
export interface RecentDecision {
  paper_id: string;
  title: string;
  decision: string;
  confidence: number;
  reason: string;
  matched_inclusion: string[];
  matched_exclusion: string[];
  is_conflict: boolean;
  timestamp: string;
}

// Real-time progress data for a workflow stage
export interface StageProgress {
  // Common fields
  phase?: string;
  thought_process?: string;
  estimated_remaining_seconds?: number;
  updated_at?: string;

  // Current item being processed
  current_item?: {
    id: string;
    title: string;
    index: number;
  };

  // Summary statistics
  summary?: {
    total?: number;
    included?: number;
    excluded?: number;
    maybe?: number;
    conflicts?: number;
    fetched?: number;
    failed?: number;
  };

  // Rolling buffer of recent decisions/events
  recent_decisions: RecentDecision[] | Record<string, unknown>[];

  // For search stage
  current_database?: string;
  databases_completed: string[];
  queries: Record<string, string>;
  results_per_database: Record<string, number>;

  // For writing stages
  current_subsection?: string;
  subsections_completed: string[];
  subsections_pending: string[];
  word_count: number;
}

export interface StageCheckpoint {
  stage: string;
  status: StageStatus;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  error_message: string | null;
  cost: number;

  // Real-time progress data
  progress?: StageProgress | null;
}

export interface WorkflowCreateRequest {
  research_question: string;
  inclusion_criteria: string;
  exclusion_criteria: string;
  databases?: string[];
  max_results_per_query?: number;
  fast_mode?: boolean;
  skip_analysis?: boolean;
  skip_writing?: boolean;
}

export interface WorkflowResponse {
  id: string;
  research_question: string;
  inclusion_criteria: string | null;
  exclusion_criteria: string | null;
  databases: string[] | null;
  status: WorkflowStatus;
  current_stage: WorkflowStage | null;
  papers_found: number;
  papers_screened: number;
  papers_included: number;
  total_cost: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;

  // New fields for unified workflow
  needs_user_action: boolean;
  action_required: string | null;
  meta_analysis_feasible: boolean | null;
  stages: StageCheckpoint[];

  // Figure URLs from R2
  forest_plot_url: string | null;
  funnel_plot_url: string | null;
  prisma_url: string | null;
}

export interface WorkflowListResponse {
  workflows: WorkflowResponse[];
  total: number;
}

export interface StageRerunRequest {
  input_override?: Record<string, unknown>;
}

export interface StageRerunResponse {
  success: boolean;
  stage: string;
  output_data: Record<string, unknown> | null;
  error: string | null;
  cost: number;
}

export const AVAILABLE_DATABASES = [
  { id: 'pubmed', label: 'PubMed', description: 'NCBI biomedical literature (recommended, most reliable)' },
  { id: 'openalex', label: 'OpenAlex', description: 'Open scholarly metadata (reliable)' },
  { id: 'semantic_scholar', label: 'Semantic Scholar', description: 'AI-powered search (strict rate limits)' },
] as const;

// Stage configuration for UI display
export const WORKFLOW_STAGES = [
  { key: 'search', label: 'Searching databases', description: 'Finding relevant papers' },
  { key: 'screen', label: 'Screening papers', description: 'AI-powered paper screening (no limit)' },
  { key: 'pdf_fetch', label: 'Fetching PDFs', description: 'Downloading full texts' },
  { key: 'extract', label: 'Extracting data', description: 'Structured data extraction' },
  { key: 'rob', label: 'Risk of Bias', description: 'Quality assessment (RoB 2/ROBINS-I/QUADAS-2)' },
  { key: 'analysis', label: 'Meta-analysis', description: 'Statistical synthesis with plots' },
  { key: 'prisma', label: 'PRISMA diagram', description: 'Flow diagram generation' },
  { key: 'tables', label: 'Generating tables', description: 'Characteristics, RoB, GRADE' },
  { key: 'introduction', label: 'Writing introduction', description: 'Background and objectives' },
  { key: 'methods', label: 'Writing methods', description: 'PRISMA-compliant methods' },
  { key: 'results', label: 'Writing results', description: 'Synthesis and findings' },
  { key: 'discussion', label: 'Writing discussion', description: 'Interpretation and implications' },
] as const;
