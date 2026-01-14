// Chat types for workflow creation flow

export type ChatStage =
  | 'welcome'
  | 'question'
  | 'inclusion'
  | 'exclusion'
  | 'databases'
  | 'confirm'
  | 'creating'
  | 'complete';

export type MessageRole = 'system' | 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  metadata?: {
    stage?: ChatStage;
    showDatabaseSelector?: boolean;
    showConfirmButton?: boolean;
    isLoading?: boolean;
  };
}

export interface WorkflowFormData {
  research_question: string;
  inclusion_criteria: string;
  exclusion_criteria: string;
  databases: string[];
  max_results_per_query: number;
  fast_mode: boolean;
}

export const DEFAULT_WORKFLOW_FORM: WorkflowFormData = {
  research_question: '',
  inclusion_criteria: '',
  exclusion_criteria: '',
  databases: ['pubmed', 'openalex'],
  max_results_per_query: 500,
  fast_mode: false,
};
