'use client';

import { Search, Filter, Download, Database, FileText, BarChart3 } from 'lucide-react';

const CAPABILITIES = [
  {
    number: '01',
    icon: Search,
    title: 'Search & Import',
    description: 'Cross-database queries, AI keyword expansion, deduplication logic',
    color: 'purple',
  },
  {
    number: '02',
    icon: Filter,
    title: 'Screening',
    description: 'AI pre-screening with confidence scores, human override, conflict flagging',
    color: 'blue',
  },
  {
    number: '03',
    icon: Download,
    title: 'Full Text Retrieval',
    description: 'Auto download where possible, manual fallback, status tracking',
    color: 'green',
  },
  {
    number: '04',
    icon: Database,
    title: 'Extraction & Synthesis',
    description: 'AI-suggested structured fields, meta-analysis, publication synthesis',
    color: 'orange',
  },
  {
    number: '05',
    icon: FileText,
    title: 'Reporting & Export',
    description: 'PRISMA flow diagrams, versioning, export to DOCX/PDF, CSV, audit logs',
    color: 'pink',
  },
  {
    number: '06',
    icon: BarChart3,
    title: 'Analytics & Insights',
    description: 'Visual dashboards, trend analysis, collaboration metrics',
    color: 'cyan',
  },
];

const colorClasses = {
  purple: { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-200' },
  blue: { bg: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-200' },
  green: { bg: 'bg-green-100', text: 'text-green-600', border: 'border-green-200' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-600', border: 'border-orange-200' },
  pink: { bg: 'bg-pink-100', text: 'text-pink-600', border: 'border-pink-200' },
  cyan: { bg: 'bg-cyan-100', text: 'text-cyan-600', border: 'border-cyan-200' },
};

export function Capabilities() {
  return (
    <section id="capabilities" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            Core Capabilities That Power Every Review
          </h2>
          <p className="mt-4 text-lg text-gray-600 max-w-3xl mx-auto">
            End-to-end workflow designed to accelerate research from project setup to PRISMA-compliant reporting, all guided by AI and verified by you.
          </p>
        </div>

        {/* Capability Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {CAPABILITIES.map((capability) => {
            const colors = colorClasses[capability.color as keyof typeof colorClasses];
            return (
              <div
                key={capability.number}
                className={`relative bg-white rounded-2xl p-6 border ${colors.border} hover:shadow-lg transition-all group`}
              >
                {/* Number Badge */}
                <div className={`absolute -top-3 -left-3 w-10 h-10 ${colors.bg} rounded-xl flex items-center justify-center border-4 border-white shadow-sm`}>
                  <span className={`text-sm font-bold ${colors.text}`}>
                    {capability.number}
                  </span>
                </div>

                {/* Icon */}
                <div className={`w-12 h-12 ${colors.bg} rounded-xl flex items-center justify-center mb-4 mt-2`}>
                  <capability.icon className={`w-6 h-6 ${colors.text}`} />
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {capability.title}
                </h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {capability.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
