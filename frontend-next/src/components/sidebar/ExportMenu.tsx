'use client';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useManuscript } from '@/hooks';
import { useStore } from '@/store';
import { toast } from 'sonner';
import type { ManuscriptExportFormat } from '@/types';
import {
  Download,
  FileJson,
  FileText,
  FileType,
  File,
  Loader2,
} from 'lucide-react';

const EXPORT_OPTIONS: {
  format: ManuscriptExportFormat;
  label: string;
  icon: typeof FileJson;
}[] = [
  { format: 'json', label: 'JSON', icon: FileJson },
  { format: 'markdown', label: 'Markdown', icon: FileText },
  { format: 'pdf', label: 'PDF', icon: File },
  { format: 'docx', label: 'Word (DOCX)', icon: FileType },
];

export function ExportMenu() {
  const { workflow } = useStore();
  const { exportManuscript, isExporting } = useManuscript();

  const handleExport = async (format: ManuscriptExportFormat) => {
    if (!workflow.current?.id) {
      toast.error('No workflow selected');
      return;
    }

    try {
      await exportManuscript(workflow.current.id, format);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Export failed';
      toast.error(message);
    }
  };

  const isDisabled = !workflow.current || workflow.current.status !== 'completed';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={isDisabled}
          className="gap-2"
        >
          {isExporting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {EXPORT_OPTIONS.map(({ format, label, icon: Icon }) => (
          <DropdownMenuItem
            key={format}
            onClick={() => handleExport(format)}
            disabled={isExporting === format}
          >
            {isExporting === format ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Icon className="w-4 h-4 mr-2" />
            )}
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
