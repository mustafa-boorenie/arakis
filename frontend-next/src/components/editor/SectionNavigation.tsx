'use client';

import { cn } from '@/lib/utils';
import { MANUSCRIPT_SECTIONS } from '@/types';
import { useStore } from '@/store';
import { Button } from '@/components/ui/button';
import {
  FileText,
  AlignLeft,
  BookOpen,
  Beaker,
  BarChart2,
  MessageSquare,
  CheckCircle,
} from 'lucide-react';

const SECTION_ICONS: Record<string, typeof FileText> = {
  title: FileText,
  abstract: AlignLeft,
  introduction: BookOpen,
  methods: Beaker,
  results: BarChart2,
  discussion: MessageSquare,
  conclusions: CheckCircle,
};

interface SectionNavigationProps {
  onSectionClick: (sectionId: string) => void;
}

export function SectionNavigation({ onSectionClick }: SectionNavigationProps) {
  const { editor } = useStore();

  return (
    <nav className="fixed left-[350px] top-1/2 -translate-y-1/2 bg-background border rounded-lg shadow-lg p-2 z-50 hidden xl:block">
      <ul className="space-y-1">
        {MANUSCRIPT_SECTIONS.map((section) => {
          const Icon = SECTION_ICONS[section.id] || FileText;
          const isActive = editor.activeSection === section.id;

          return (
            <li key={section.id}>
              <Button
                variant={isActive ? 'secondary' : 'ghost'}
                size="sm"
                className={cn(
                  'w-full justify-start gap-2',
                  isActive && 'bg-primary/10 text-primary'
                )}
                onClick={() => onSectionClick(section.id)}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden 2xl:inline">{section.label}</span>
              </Button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
