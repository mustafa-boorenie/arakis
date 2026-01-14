'use client';

import { Card } from '@/components/ui/card';
import { API_BASE_URL } from '@/lib/api/client';
import type { Figure } from '@/types';
import { ImageOff } from 'lucide-react';

interface FigureRendererProps {
  figure: Figure;
}

export function FigureRenderer({ figure }: FigureRendererProps) {
  // Construct full URL for figure - prepend API base URL if path starts with /api
  const figureUrl = figure.file_path?.startsWith('/api')
    ? `${API_BASE_URL}${figure.file_path}`
    : figure.file_path;

  return (
    <Card className="my-6 p-4 text-center">
      <div className="relative bg-muted rounded-lg flex items-center justify-center overflow-hidden p-4">
        {figureUrl ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={figureUrl}
            alt={figure.title}
            className="max-w-full h-auto object-contain"
            style={{ maxHeight: '600px' }}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <ImageOff className="w-12 h-12" />
            <span className="text-sm">Figure not available</span>
          </div>
        )}
      </div>
      <div className="mt-3 text-sm">
        <p className="font-semibold">{figure.id}: {figure.title}</p>
        <p className="text-muted-foreground italic mt-1">{figure.caption}</p>
      </div>
    </Card>
  );
}
