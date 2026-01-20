'use client';

import { Clock, Users, Lock, Shield } from 'lucide-react';

const PROBLEMS = [
  {
    icon: Clock,
    title: 'Time drain',
    description: 'Traditional reviews take 18-24 months to complete',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
  },
  {
    icon: Users,
    title: 'Inconsistency & human error',
    description: 'Manual screening is laborious and error-prone',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
  },
  {
    icon: Lock,
    title: 'Access barriers',
    description: 'Many full texts are behind barrier paywalls',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
  },
  {
    icon: Shield,
    title: 'Compliance risks',
    description: 'Journals require rigorous audit and reproducibility',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
];

export function WhyArakis() {
  return (
    <section id="why-arakis" className="py-20 px-4 sm:px-6 lg:px-8 bg-purple-50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            Why{' '}
            <span className="bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
              Arakis.AI
            </span>{' '}
            Matters
          </h2>
          <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
            Research teams face growing challenges including slow timelines, high attrition, and the quality of evidence-based decisions.
          </p>
        </div>

        {/* Problem Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {PROBLEMS.map((problem) => (
            <div
              key={problem.title}
              className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
            >
              <div className={`w-12 h-12 ${problem.bgColor} rounded-xl flex items-center justify-center mb-4`}>
                <problem.icon className={`w-6 h-6 ${problem.color}`} />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {problem.title}
              </h3>
              <p className="text-gray-600 text-sm">
                {problem.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
