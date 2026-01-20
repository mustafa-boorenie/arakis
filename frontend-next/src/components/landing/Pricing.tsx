'use client';

import { useState } from 'react';
import { Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

const PLANS = [
  {
    name: 'Academic Plan',
    price: { monthly: 49, annual: 39 },
    description: 'For students & researchers',
    features: [
      'Access to all workflows',
      'Up to 5 active projects',
      'AI screening & extraction',
      '50 papers/review limit',
      'Export to DOCX/PDF',
      'Email support',
    ],
    highlighted: false,
    cta: 'Start Free Trial',
  },
  {
    name: 'Professional Plan',
    price: { monthly: 149, annual: 119 },
    description: 'For experienced reviewers',
    features: [
      'Unlimited active projects',
      'Unlimited papers per review',
      'Priority AI processing',
      'Team collaboration (up to 10)',
      'Advanced analytics',
      'API access',
      'Priority support',
    ],
    highlighted: true,
    cta: 'Start Free Trial',
    badge: 'Most Popular',
  },
  {
    name: 'Enterprise Plan',
    price: { monthly: null, annual: null },
    description: 'For institutions & enterprises',
    features: [
      'Everything in Professional',
      'Unlimited team members',
      'Custom integrations',
      'SSO / SAML authentication',
      'Dedicated account manager',
      'On-premise deployment option',
      'Custom SLA',
      'Training & onboarding',
    ],
    highlighted: false,
    cta: 'Contact Sales',
  },
];

interface PricingProps {
  onStartTrial: () => void;
}

export function Pricing({ onStartTrial }: PricingProps) {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            Simple, Transparent Pricing for Every Researcher
          </h2>
          <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
            Whether you&apos;re a student, an independent reviewer, or a large institution, Arakis AI scales with your needs.
          </p>

          {/* Billing Toggle */}
          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                billingCycle === 'monthly'
                  ? 'bg-purple-100 text-purple-700'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('annual')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                billingCycle === 'annual'
                  ? 'bg-purple-100 text-purple-700'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Annual
              <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                Save 20%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-8 ${
                plan.highlighted
                  ? 'bg-purple-600 text-white shadow-xl shadow-purple-500/25 scale-105'
                  : 'bg-white border border-gray-200'
              }`}
            >
              {/* Badge */}
              {plan.badge && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="bg-orange-400 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    {plan.badge}
                  </span>
                </div>
              )}

              {/* Plan Name */}
              <h3 className={`text-xl font-bold ${plan.highlighted ? 'text-white' : 'text-gray-900'}`}>
                {plan.name}
              </h3>

              {/* Price */}
              <div className="mt-4 mb-2">
                {plan.price.monthly !== null ? (
                  <div className="flex items-baseline gap-1">
                    <span className={`text-4xl font-bold ${plan.highlighted ? 'text-white' : 'text-gray-900'}`}>
                      ${billingCycle === 'monthly' ? plan.price.monthly : plan.price.annual}
                    </span>
                    <span className={`text-sm ${plan.highlighted ? 'text-purple-200' : 'text-gray-500'}`}>
                      /month
                    </span>
                  </div>
                ) : (
                  <span className={`text-2xl font-bold ${plan.highlighted ? 'text-white' : 'text-gray-900'}`}>
                    Custom Pricing
                  </span>
                )}
              </div>

              {/* Description */}
              <p className={`text-sm mb-6 ${plan.highlighted ? 'text-purple-200' : 'text-gray-500'}`}>
                {plan.description}
              </p>

              {/* Features */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check className={`w-5 h-5 flex-shrink-0 ${plan.highlighted ? 'text-purple-200' : 'text-purple-600'}`} />
                    <span className={`text-sm ${plan.highlighted ? 'text-purple-100' : 'text-gray-600'}`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Button
                onClick={plan.cta === 'Contact Sales' ? undefined : onStartTrial}
                className={`w-full ${
                  plan.highlighted
                    ? 'bg-white text-purple-600 hover:bg-purple-50'
                    : 'bg-purple-600 text-white hover:bg-purple-700'
                }`}
                size="lg"
              >
                {plan.cta}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
