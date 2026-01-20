'use client';

import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeroProps {
  onStartTrial: () => void;
  onWatchDemo?: () => void;
}

export function Hero({ onStartTrial, onWatchDemo }: HeroProps) {
  return (
    <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-purple-50/50 to-white">
      <div className="max-w-7xl mx-auto">
        {/* Main Headline */}
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight">
            Automate Your{' '}
            <span className="relative">
              <span className="bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
                Systematic Reviews
              </span>
              <svg
                className="absolute -bottom-2 left-0 w-full"
                viewBox="0 0 300 12"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M2 10C50 4 100 2 150 6C200 10 250 4 298 8"
                  stroke="url(#underline-gradient)"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                <defs>
                  <linearGradient id="underline-gradient" x1="0" y1="0" x2="300" y2="0">
                    <stop offset="0%" stopColor="#9333ea" />
                    <stop offset="100%" stopColor="#7c3aed" />
                  </linearGradient>
                </defs>
              </svg>
            </span>
            . Finish in Days, Not Months
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto">
            A next-gen platform combining AI and human oversight, built to deliver PRISMA-compliant reviews with transparency, accuracy, and speed.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              onClick={onStartTrial}
              size="lg"
              className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-6 text-lg rounded-xl shadow-lg shadow-purple-500/25"
            >
              Start Free Trial
            </Button>
            <Button
              onClick={onWatchDemo}
              variant="outline"
              size="lg"
              className="px-8 py-6 text-lg rounded-xl border-gray-300 hover:bg-gray-50"
            >
              <Play className="w-5 h-5 mr-2" />
              Watch Demo
            </Button>
          </div>
        </div>

        {/* Product Screenshot */}
        <div className="mt-16 relative">
          <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent z-10 pointer-events-none" />
          <div className="relative bg-white rounded-2xl shadow-2xl shadow-purple-500/10 border border-gray-200 overflow-hidden mx-auto max-w-5xl">
            {/* Browser Chrome */}
            <div className="bg-gray-100 px-4 py-3 flex items-center gap-2 border-b border-gray-200">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
              </div>
              <div className="flex-1 mx-4">
                <div className="bg-white rounded-md px-3 py-1.5 text-sm text-gray-500 max-w-md mx-auto">
                  app.arakis.ai
                </div>
              </div>
            </div>

            {/* App Preview Content */}
            <div className="bg-gray-50 p-8">
              <div className="flex gap-4">
                {/* Sidebar Preview */}
                <div className="w-64 bg-white rounded-lg border border-gray-200 p-4 hidden sm:block">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 bg-purple-100 rounded-lg" />
                    <div className="flex-1">
                      <div className="h-3 bg-gray-200 rounded w-20 mb-1" />
                      <div className="h-2 bg-gray-100 rounded w-16" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-10 bg-purple-50 rounded-lg border border-purple-100" />
                    <div className="h-10 bg-gray-50 rounded-lg" />
                    <div className="h-10 bg-gray-50 rounded-lg" />
                  </div>
                </div>

                {/* Main Content Preview */}
                <div className="flex-1 bg-white rounded-lg border border-gray-200 p-6">
                  <div className="text-center mb-6">
                    <div className="h-6 bg-gray-200 rounded w-64 mx-auto mb-2" />
                    <div className="h-4 bg-gray-100 rounded w-48 mx-auto" />
                  </div>
                  <div className="space-y-3">
                    <div className="h-12 bg-purple-50 rounded-xl border border-purple-100 flex items-center px-4">
                      <div className="h-3 bg-purple-200 rounded w-3/4" />
                    </div>
                    <div className="flex gap-2 justify-center">
                      <div className="h-8 bg-gray-100 rounded-full px-4 w-32" />
                      <div className="h-8 bg-gray-100 rounded-full px-4 w-40" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tagline below screenshot */}
          <p className="text-center mt-8 text-lg text-gray-600 font-medium">
            Condense <span className="text-purple-600">Hours</span> into <span className="text-purple-600">Minutes</span>
          </p>
        </div>
      </div>
    </section>
  );
}
