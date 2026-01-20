'use client';

import { Star } from 'lucide-react';

const TESTIMONIALS = [
  {
    quote: "Arakis cut our systematic review timeline from 18 months to just 6 weeks. The AI screening is remarkably accurate, and the dual-review feature gives us confidence in our results.",
    author: 'Dr. Laura Chen',
    role: 'Clinical Researcher',
    institution: 'University of Toronto',
    avatar: 'LC',
    avatarBg: 'bg-purple-100',
    avatarText: 'text-purple-600',
  },
  {
    quote: "The PRISMA-compliant exports saved us countless hours of formatting. We can now focus on the science rather than the paperwork. A game-changer for our WHO collaborating centre.",
    author: 'Dr. Ashkaya Dinesh',
    role: 'Public Health Analyst',
    institution: 'WHO Collaborating Centre',
    avatar: 'AD',
    avatarBg: 'bg-blue-100',
    avatarText: 'text-blue-600',
  },
  {
    quote: "As a journal editor, I can verify that reviews conducted with Arakis meet our rigorous standards. The audit trail and reproducibility features are exactly what evidence-based medicine needs.",
    author: 'Dr. Priyanka Sharma',
    role: 'Journal Editor',
    institution: 'Evidence & Practice',
    avatar: 'PS',
    avatarBg: 'bg-green-100',
    avatarText: 'text-green-600',
  },
];

export function Testimonials() {
  return (
    <section id="testimonials" className="py-20 px-4 sm:px-6 lg:px-8 bg-purple-50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            Trusted by Researchers and Institutions Worldwide
          </h2>
          <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
            See how Arakis AI is transforming systematic workflows with unmatched accuracy and transparency.
          </p>
        </div>

        {/* Testimonial Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {TESTIMONIALS.map((testimonial) => (
            <div
              key={testimonial.author}
              className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
            >
              {/* Stars */}
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                ))}
              </div>

              {/* Quote */}
              <blockquote className="text-gray-700 leading-relaxed mb-6">
                &ldquo;{testimonial.quote}&rdquo;
              </blockquote>

              {/* Author */}
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-full ${testimonial.avatarBg} flex items-center justify-center`}>
                  <span className={`text-sm font-semibold ${testimonial.avatarText}`}>
                    {testimonial.avatar}
                  </span>
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{testimonial.author}</p>
                  <p className="text-sm text-gray-500">
                    {testimonial.role}, {testimonial.institution}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
