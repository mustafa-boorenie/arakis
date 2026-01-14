'use client';

import { useCallback, useState } from 'react';
import { api, downloadBlob } from '@/lib/api/client';
import { useStore } from '@/store';
import type { ManuscriptExportFormat } from '@/types';

export function useManuscript() {
  const { editor, setManuscript, setActiveSection, setEditorLoading } = useStore();
  const [isExporting, setIsExporting] = useState<ManuscriptExportFormat | null>(null);

  const loadManuscript = useCallback(
    async (workflowId: string) => {
      setEditorLoading(true);
      try {
        const manuscript = await api.getManuscript(workflowId);
        setManuscript(manuscript);
        return manuscript;
      } finally {
        setEditorLoading(false);
      }
    },
    [setManuscript, setEditorLoading]
  );

  const exportManuscript = useCallback(
    async (workflowId: string, format: ManuscriptExportFormat) => {
      setIsExporting(format);
      try {
        let blob: Blob;
        let filename: string;
        const timestamp = new Date().toISOString().split('T')[0];

        switch (format) {
          case 'json':
            const data = await api.getManuscript(workflowId);
            blob = new Blob([JSON.stringify(data, null, 2)], {
              type: 'application/json',
            });
            filename = `manuscript_${timestamp}.json`;
            break;
          case 'markdown':
            blob = await api.exportMarkdown(workflowId);
            filename = `manuscript_${timestamp}.md`;
            break;
          case 'pdf':
            blob = await api.exportPdf(workflowId);
            filename = `manuscript_${timestamp}.pdf`;
            break;
          case 'docx':
            blob = await api.exportDocx(workflowId);
            filename = `manuscript_${timestamp}.docx`;
            break;
          default:
            throw new Error(`Unsupported format: ${format}`);
        }

        downloadBlob(blob, filename);
        return true;
      } catch (error) {
        console.error(`Export to ${format} failed:`, error);
        throw error;
      } finally {
        setIsExporting(null);
      }
    },
    []
  );

  return {
    manuscript: editor.manuscript,
    activeSection: editor.activeSection,
    isLoading: editor.isLoading,
    isDirty: editor.isDirty,
    isExporting,
    loadManuscript,
    exportManuscript,
    setActiveSection,
  };
}
