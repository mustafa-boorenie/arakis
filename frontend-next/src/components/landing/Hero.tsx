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

        {/* Demo Video */}
        <div className="mt-16 relative">
          <div className="relative rounded-2xl shadow-2xl shadow-purple-500/20 overflow-hidden mx-auto max-w-5xl">
            <video
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-auto rounded-2xl"
              poster="/videos/hero-demo-poster.jpg"
            >
              <source src="/videos/hero-demo.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>

            {/* Gradient overlay with tagline */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent pt-20 pb-6 px-6 pointer-events-none">
              <p className="text-center text-lg sm:text-xl text-white font-medium">
                From research question to <span className="text-purple-300">publication-ready manuscript</span> in minutes
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
