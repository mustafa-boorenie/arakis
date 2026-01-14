// TypeScript types matching backend schemas from:
// src/arakis/api/schemas/manuscript.py

export interface WorkflowMetadata {
  workflow_id: string;
  research_question: string;
  papers_found: number;
  papers_included: number;
  total_cost: number;
  databases_searched: string[];
}

export interface Figure {
  id: string;
  title: string;
  caption: string;
  file_path: string | null;
  figure_type: 'forest_plot' | 'funnel_plot' | 'prisma_diagram' | string;
}

export interface Table {
  id: string;
  title: string;
  headers: string[];
  rows: unknown[][];
  footnotes: string[] | null;
}

export interface Reference {
  id: string;
  citation: string;
  doi: string | null;
}

export interface Manuscript {
  title: string;
  abstract: string;
  introduction: string;
  methods: string;
  results: string;
  discussion: string;
  conclusions: string;
}

export interface ManuscriptResponse {
  metadata: WorkflowMetadata;
  manuscript: Manuscript;
  figures: Figure[];
  tables: Table[];
  references: Reference[];
  statistics: Record<string, unknown> | null;
}

export type ManuscriptExportFormat = 'json' | 'markdown' | 'pdf' | 'docx';

export const MANUSCRIPT_SECTIONS = [
  { id: 'title', label: 'Title' },
  { id: 'abstract', label: 'Abstract' },
  { id: 'introduction', label: 'Introduction' },
  { id: 'methods', label: 'Methods' },
  { id: 'results', label: 'Results' },
  { id: 'discussion', label: 'Discussion' },
  { id: 'conclusions', label: 'Conclusions' },
] as const;
