'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const FAQS = [
  {
    question: 'How much faster is it compared to traditional review methods?',
    answer: 'Arakis AI typically reduces systematic review timelines from 18-24 months to 4-8 weeks. The AI-powered screening and extraction can process hundreds of papers in hours rather than weeks, while maintaining the rigorous standards required for publication.',
  },
  {
    question: 'Which databases does Arakis AI connect to?',
    answer: 'Arakis AI connects to major academic databases including PubMed, OpenAlex, Semantic Scholar, and more. We support cross-database searching with automatic deduplication, ensuring comprehensive coverage of the literature.',
  },
  {
    question: 'Can I collaborate with my research team?',
    answer: 'Yes! Arakis AI supports team collaboration with role-based permissions, real-time updates, and conflict resolution features. Multiple reviewers can work simultaneously on screening, extraction, and quality assessment.',
  },
  {
    question: 'Does Arakis AI follow PRISMA standards?',
    answer: 'Absolutely. Arakis AI is designed with PRISMA 2020 guidelines at its core. We automatically generate PRISMA flow diagrams, track all inclusion/exclusion decisions with full audit trails, and ensure your reviews meet publication standards.',
  },
  {
    question: 'What about data security and privacy?',
    answer: 'We take security seriously. All data is encrypted in transit and at rest. We are SOC 2 compliant and follow GDPR guidelines. Your research data is never shared with third parties or used to train AI models.',
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-3xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Everything you need to know about Arakis AI, from setup to security, collaboration, and pricing.
          </p>
        </div>

        {/* FAQ Accordion */}
        <div className="space-y-4">
          {FAQS.map((faq, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex items-center justify-between p-5 text-left bg-white hover:bg-gray-50 transition-colors"
              >
                <span className="font-medium text-gray-900 pr-4">
                  {faq.question}
                </span>
                <ChevronDown
                  className={`w-5 h-5 text-gray-500 flex-shrink-0 transition-transform ${
                    openIndex === index ? 'rotate-180' : ''
                  }`}
                />
              </button>
              {openIndex === index && (
                <div className="px-5 pb-5">
                  <p className="text-gray-600 leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
