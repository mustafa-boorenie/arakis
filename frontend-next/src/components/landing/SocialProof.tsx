'use client';

const COMPANIES = [
  { name: 'FinEdge', color: '#6366f1' },
  { name: 'Quantum', color: '#8b5cf6' },
  { name: 'MedFlow', color: '#06b6d4' },
  { name: 'Stratus', color: '#10b981' },
  { name: 'NexGen', color: '#f59e0b' },
];

export function SocialProof() {
  return (
    <section className="py-12 px-4 sm:px-6 lg:px-8 bg-white border-y border-gray-100">
      <div className="max-w-7xl mx-auto">
        <p className="text-center text-sm text-gray-500 mb-8">
          Just a few of the companies we&apos;ve supported over the years
        </p>

        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16">
          {COMPANIES.map((company) => (
            <div
              key={company.name}
              className="flex items-center gap-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              {/* Placeholder logo - geometric shape */}
              <div
                className="w-8 h-8 rounded-lg opacity-60"
                style={{ backgroundColor: company.color }}
              />
              <span className="text-lg font-semibold">{company.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
