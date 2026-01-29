import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  Easing,
} from 'remotion';
import { IntroScene } from './components/IntroScene';
import { ChatScene } from './components/ChatScene';
import { WorkflowScene } from './components/WorkflowScene';
import { OutputScene } from './components/OutputScene';
import { OutroScene } from './components/OutroScene';

export const ArakisWorkflow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scene timings (in frames at 30fps)
  const INTRO_START = 0;
  const INTRO_DURATION = 90; // 3 seconds

  const CHAT_START = INTRO_DURATION;
  const CHAT_DURATION = 180; // 6 seconds

  const WORKFLOW_START = CHAT_START + CHAT_DURATION;
  const WORKFLOW_DURATION = 450; // 15 seconds

  const OUTPUT_START = WORKFLOW_START + WORKFLOW_DURATION;
  const OUTPUT_DURATION = 120; // 4 seconds

  const OUTRO_START = OUTPUT_START + OUTPUT_DURATION;
  const OUTRO_DURATION = 60; // 2 seconds

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0f',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Background gradient animation */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at ${50 + Math.sin(frame / 60) * 10}% ${50 + Math.cos(frame / 80) * 10}%, rgba(139, 92, 246, 0.15) 0%, transparent 50%)`,
        }}
      />

      {/* Scene 1: Intro */}
      <Sequence from={INTRO_START} durationInFrames={INTRO_DURATION}>
        <IntroScene />
      </Sequence>

      {/* Scene 2: Chat Interface */}
      <Sequence from={CHAT_START} durationInFrames={CHAT_DURATION}>
        <ChatScene />
      </Sequence>

      {/* Scene 3: Workflow Progress */}
      <Sequence from={WORKFLOW_START} durationInFrames={WORKFLOW_DURATION}>
        <WorkflowScene />
      </Sequence>

      {/* Scene 4: Output/Manuscript */}
      <Sequence from={OUTPUT_START} durationInFrames={OUTPUT_DURATION}>
        <OutputScene />
      </Sequence>

      {/* Scene 5: Outro */}
      <Sequence from={OUTRO_START} durationInFrames={OUTRO_DURATION}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
