'use client';

import { Card } from '@/components/ui/card';
import type { Figure } from '@/types';
import { ImageOff } from 'lucide-react';

interface FigureRendererProps {
  figure: Figure;
}

export function FigureRenderer({ figure }: FigureRendererProps) {
  return (
    <Card className="my-6 p-4 text-center">
      <div className="relative aspect-video bg-muted rounded-lg flex items-center justify-center overflow-hidden">
        {figure.file_path ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={figure.file_path}
            alt={figure.title}
            className="max-w-full max-h-full object-contain"
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
