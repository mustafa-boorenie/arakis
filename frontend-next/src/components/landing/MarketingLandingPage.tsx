'use client';

import { LandingHeader } from './LandingHeader';
import { Hero } from './Hero';
import { SocialProof } from './SocialProof';
import { WhyArakis } from './WhyArakis';
import { Capabilities } from './Capabilities';
import { HowItWorks } from './HowItWorks';
import { Pricing } from './Pricing';
import { Testimonials } from './Testimonials';
import { FAQ } from './FAQ';
import { FinalCTA } from './FinalCTA';
import { LandingFooter } from './LandingFooter';

interface MarketingLandingPageProps {
  onStartTrial: () => void;
}

export function MarketingLandingPage({ onStartTrial }: MarketingLandingPageProps) {
  const handleWatchDemo = () => {
    // Could open a modal with demo video or navigate to demo page
    console.log('Watch demo clicked');
  };

  return (
    <div className="min-h-screen bg-white">
      <LandingHeader onStartTrial={onStartTrial} />

      <main>
        <Hero onStartTrial={onStartTrial} onWatchDemo={handleWatchDemo} />
        <SocialProof />
        <WhyArakis />
        <Capabilities />
        <HowItWorks />
        <Pricing onStartTrial={onStartTrial} />
        <Testimonials />
        <FAQ />
        <FinalCTA onStartTrial={onStartTrial} />
      </main>

      <LandingFooter />
    </div>
  );
}
