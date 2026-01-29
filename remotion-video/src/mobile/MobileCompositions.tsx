import { AbsoluteFill, Sequence } from 'remotion';
import { MobileIntroScene } from './MobileIntroScene';
import { MobileChatScene } from './MobileChatScene';
import { MobileWorkflowScene } from './MobileWorkflowScene';
import { MobileOutputScene } from './MobileOutputScene';
import { MobileOutroScene } from './MobileOutroScene';
import {
  MobileTimeSaverIntro,
  MobileTimeSaverOutro,
  MobileCostEffectiveIntro,
  MobileCostEffectiveOutro,
  MobileAcademicIntro,
  MobileAcademicOutro,
} from './MobileVariations';

const MobileBackground: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ backgroundColor: '#0a0a0f', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
    {children}
  </AbsoluteFill>
);

// Original mobile video
export const MobileArakisWorkflow: React.FC = () => (
  <MobileBackground>
    <Sequence from={0} durationInFrames={90}>
      <MobileIntroScene />
    </Sequence>
    <Sequence from={90} durationInFrames={180}>
      <MobileChatScene />
    </Sequence>
    <Sequence from={270} durationInFrames={450}>
      <MobileWorkflowScene />
    </Sequence>
    <Sequence from={720} durationInFrames={120}>
      <MobileOutputScene />
    </Sequence>
    <Sequence from={840} durationInFrames={60}>
      <MobileOutroScene />
    </Sequence>
  </MobileBackground>
);

// Time Saver variation
export const MobileTimeSaver: React.FC = () => (
  <MobileBackground>
    <Sequence from={0} durationInFrames={90}>
      <MobileTimeSaverIntro />
    </Sequence>
    <Sequence from={90} durationInFrames={180}>
      <MobileChatScene />
    </Sequence>
    <Sequence from={270} durationInFrames={450}>
      <MobileWorkflowScene />
    </Sequence>
    <Sequence from={720} durationInFrames={120}>
      <MobileOutputScene />
    </Sequence>
    <Sequence from={840} durationInFrames={60}>
      <MobileTimeSaverOutro />
    </Sequence>
  </MobileBackground>
);

// Cost Effective variation
export const MobileCostEffective: React.FC = () => (
  <MobileBackground>
    <Sequence from={0} durationInFrames={90}>
      <MobileCostEffectiveIntro />
    </Sequence>
    <Sequence from={90} durationInFrames={180}>
      <MobileChatScene />
    </Sequence>
    <Sequence from={270} durationInFrames={450}>
      <MobileWorkflowScene />
    </Sequence>
    <Sequence from={720} durationInFrames={120}>
      <MobileOutputScene />
    </Sequence>
    <Sequence from={840} durationInFrames={60}>
      <MobileCostEffectiveOutro />
    </Sequence>
  </MobileBackground>
);

// Academic variation
export const MobileAcademic: React.FC = () => (
  <MobileBackground>
    <Sequence from={0} durationInFrames={90}>
      <MobileAcademicIntro />
    </Sequence>
    <Sequence from={90} durationInFrames={180}>
      <MobileChatScene />
    </Sequence>
    <Sequence from={270} durationInFrames={450}>
      <MobileWorkflowScene />
    </Sequence>
    <Sequence from={720} durationInFrames={120}>
      <MobileOutputScene />
    </Sequence>
    <Sequence from={840} durationInFrames={60}>
      <MobileAcademicOutro />
    </Sequence>
  </MobileBackground>
);
