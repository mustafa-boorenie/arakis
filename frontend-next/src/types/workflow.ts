// TypeScript types matching backend schemas from:
// src/arakis/api/schemas/workflow.py

export type WorkflowStatus = 'pending' | 'running' | 'needs_review' | 'completed' | 'failed';

export type WorkflowStage =
  | 'searching'
  | 'screening'
  | 'analyzing'
  | 'writing'
  | 'finalizing'
  | 'completed';

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
}

export interface WorkflowListResponse {
  workflows: WorkflowResponse[];
  total: number;
}

export const AVAILABLE_DATABASES = [
  { id: 'pubmed', label: 'PubMed', description: 'NCBI biomedical literature (recommended, most reliable)' },
  { id: 'openalex', label: 'OpenAlex', description: 'Open scholarly metadata (reliable)' },
  { id: 'semantic_scholar', label: 'Semantic Scholar', description: 'AI-powered search (strict rate limits)' },
] as const;
