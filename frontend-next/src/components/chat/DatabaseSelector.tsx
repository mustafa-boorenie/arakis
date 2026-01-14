'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { AVAILABLE_DATABASES } from '@/types';
import { Check, Database } from 'lucide-react';

interface DatabaseSelectorProps {
  selected: string[];
  onChange: (databases: string[]) => void;
  onConfirm: () => void;
}

export function DatabaseSelector({
  selected,
  onChange,
  onConfirm,
}: DatabaseSelectorProps) {
  const toggleDatabase = (id: string) => {
    if (selected.includes(id)) {
      // Don't allow deselecting all
      if (selected.length > 1) {
        onChange(selected.filter((d) => d !== id));
      }
    } else {
      onChange([...selected, id]);
    }
  };

  return (
    <div className="space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      <div className="grid gap-2">
        {AVAILABLE_DATABASES.map((db) => {
          const isSelected = selected.includes(db.id);
          return (
            <Card
              key={db.id}
              className={cn(
                'p-3 cursor-pointer transition-all hover:shadow-md',
                isSelected
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              )}
              onClick={() => toggleDatabase(db.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    )}
                  >
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{db.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {db.description}
                    </p>
                  </div>
                </div>
                {isSelected && (
                  <Badge variant="default" className="gap-1">
                    <Check className="w-3 h-3" />
                    Selected
                  </Badge>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {selected.length} database{selected.length !== 1 ? 's' : ''} selected
        </p>
        <Button onClick={onConfirm} disabled={selected.length === 0}>
          Continue
        </Button>
      </div>
    </div>
  );
}
