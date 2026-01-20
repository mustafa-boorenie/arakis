'use client';

import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface FinalCTAProps {
  onStartTrial: () => void;
}

export function FinalCTA({ onStartTrial }: FinalCTAProps) {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-purple-600 to-purple-800">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
          Ready to Accelerate Your Next Systematic Review?
        </h2>
        <p className="text-lg text-purple-200 mb-10 max-w-2xl mx-auto">
          Start your first project today and see how Arakis AI transforms months of manual work
          into a streamlined, AI-powered workflow. Free trial—no credit card required.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button
            onClick={onStartTrial}
            size="lg"
            className="bg-white text-purple-700 hover:bg-purple-50 px-8 py-6 text-lg rounded-xl shadow-lg"
          >
            Start Free Trial
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="border-2 border-white/30 text-white hover:bg-white/10 px-8 py-6 text-lg rounded-xl"
          >
            Schedule a Demo
          </Button>
        </div>
      </div>
    </section>
  );
}
