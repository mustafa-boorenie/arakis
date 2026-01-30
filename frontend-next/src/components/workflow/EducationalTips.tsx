'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lightbulb, ChevronLeft, ChevronRight, X } from 'lucide-react';

interface EducationalTipsProps {
  stage: string;
  className?: string;
  onDismiss?: () => void;
}

// Educational tips for each stage
const STAGE_TIPS: Record<string, string[]> = {
  search: [
    'PRISMA 2020 requires documenting all databases searched with dates.',
    'Different databases have different coverage - PubMed focuses on biomedical literature.',
    'MeSH terms help find relevant papers even when authors use different terminology.',
    'Limiting by date can introduce bias - consider your inclusion criteria carefully.',
  ],
  screen: [
    'Dual screening (two independent reviewers) is the gold standard for reducing bias.',
    'PRISMA requires reporting the number excluded at each stage with reasons.',
    'Abstract screening should focus on clear inclusion/exclusion criteria.',
    "When in doubt, include the paper for full-text review - it's better to over-include.",
  ],
  pdf_fetch: [
    'Many journals offer open access versions through repositories like PMC.',
    'Preprints on bioRxiv/arXiv may contain more recent findings.',
    'Contact authors directly for papers not available through open access.',
    'Check your institution library for additional access options.',
  ],
  extract: [
    'Triple extraction (3 independent reviewers) improves data accuracy.',
    'Extract data as reported - do not perform calculations or transformations.',
    'Note when data is missing or reported in non-standard formats.',
    'Keep an audit trail of all extraction decisions.',
  ],
  rob: [
    'Risk of bias assessment should be performed independently by two reviewers.',
    'RoB 2 is for randomized trials, ROBINS-I for non-randomized studies.',
    'Consider funding sources and conflicts of interest as potential bias.',
    "Don't conflate reporting quality with methodological quality.",
  ],
  analysis: [
    'High I-squared (>50%) indicates substantial heterogeneity between studies.',
    'Random-effects models are generally more appropriate than fixed-effects.',
    'Sensitivity analyses help assess robustness of findings.',
    'Consider subgroup analyses to explore sources of heterogeneity.',
  ],
  prisma: [
    'PRISMA 2020 flow diagrams have a standardized format - follow the template.',
    'Report numbers at each stage: identified, screened, assessed, included.',
    'Include reasons for exclusion at full-text screening stage.',
    'The diagram should match the numbers reported in your methods.',
  ],
  tables: [
    'Table 1 typically shows study characteristics (design, population, intervention).',
    'Risk of bias summary shows overall quality across all studies.',
    'GRADE Summary of Findings shows certainty of evidence per outcome.',
  ],
  introduction: [
    'The introduction should move from broad context to specific question.',
    'Cite systematic reviews that address related questions.',
    'State the rationale for conducting this review clearly.',
    'End with specific, measurable objectives.',
  ],
  methods: [
    'Methods should be detailed enough for replication.',
    'PRISMA 2020 has a checklist of items to include in methods.',
    'Describe any deviations from registered protocol.',
    'Report all sensitivity and subgroup analyses planned a priori.',
  ],
  results: [
    'Present results in the same order as methods.',
    'Report exact numbers with confidence intervals.',
    'Describe heterogeneity assessment results.',
    'Include sensitivity analysis results in supplementary materials.',
  ],
  discussion: [
    'Interpret findings in context of existing literature.',
    'Acknowledge limitations transparently.',
    'Discuss implications for practice and future research.',
    'Avoid overstating conclusions beyond what data supports.',
  ],
};

// Default tips shown for any stage
const DEFAULT_TIPS = [
  'Systematic reviews follow a rigorous, reproducible methodology.',
  'Document all decisions to ensure transparency and reproducibility.',
  'Consider registering your protocol with PROSPERO before starting.',
  'Use PRISMA 2020 guidelines for reporting your review.',
];

export function EducationalTips({ stage, className = '', onDismiss }: EducationalTipsProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isDismissed, setIsDismissed] = useState(false);

  // Get tips for current stage
  const tips = STAGE_TIPS[stage] || DEFAULT_TIPS;

  // Auto-rotate tips every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % tips.length);
    }, 10000);

    return () => clearInterval(interval);
  }, [tips.length]);

  // Reset index when stage changes
  useEffect(() => {
    setCurrentIndex(0);
  }, [stage]);

  if (isDismissed) return null;

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + tips.length) % tips.length);
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % tips.length);
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  return (
    <Card className={`p-4 border-purple-200 bg-purple-50 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
          <Lightbulb className="w-4 h-4 text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-sm font-medium text-purple-800">Did you know?</h4>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-purple-600 hover:text-purple-800 hover:bg-purple-100"
              onClick={handleDismiss}
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-sm text-purple-700">{tips[currentIndex]}</p>
          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-1">
              {tips.map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full transition-colors ${
                    i === currentIndex ? 'bg-purple-600' : 'bg-purple-300'
                  }`}
                />
              ))}
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-purple-600 hover:text-purple-800 hover:bg-purple-100"
                onClick={handlePrev}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-purple-600 hover:text-purple-800 hover:bg-purple-100"
                onClick={handleNext}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
