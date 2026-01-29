import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';
import { ChatScene } from '../components/ChatScene';
import { WorkflowScene } from '../components/WorkflowScene';
import { OutputScene } from '../components/OutputScene';

// Hook: Time-saving angle
const TimeSaverIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1Opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const line1Y = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });

  const strikethrough = interpolate(frame, [20, 40], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const line2Opacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const line2Scale = spring({ frame: frame - 35, fps, config: { damping: 8, stiffness: 80 } });

  const subtitleOpacity = interpolate(frame, [55, 70], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30 }}>
        {/* Old way */}
        <div
          style={{
            opacity: line1Opacity,
            transform: `translateY(${(1 - Math.min(line1Y, 1)) * 30}px)`,
            position: 'relative',
          }}
        >
          <span style={{ fontSize: 48, color: 'rgba(255, 255, 255, 0.5)', fontWeight: 500 }}>
            Weeks of manual review
          </span>
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: 0,
              height: 4,
              width: `${strikethrough}%`,
              backgroundColor: '#ef4444',
              borderRadius: 2,
            }}
          />
        </div>

        {/* New way */}
        <div
          style={{
            opacity: line2Opacity,
            transform: `scale(${Math.max(0, Math.min(line2Scale, 1.1))})`,
          }}
        >
          <span
            style={{
              fontSize: 72,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #22c55e 0%, #10b981 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            5 Minutes with AI
          </span>
        </div>

        {/* Subtitle */}
        <div style={{ opacity: subtitleOpacity, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="28" height="28" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ fontSize: 32, color: 'white', fontWeight: 600 }}>Arakis</span>
        </div>
      </div>

      {/* Clock animation */}
      <div
        style={{
          position: 'absolute',
          top: '15%',
          right: '15%',
          opacity: interpolate(frame, [10, 25, 75, 85], [0, 0.3, 0.3, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
        }}
      >
        <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      </div>
    </AbsoluteFill>
  );
};

// CTA: Save time
const TimeSaverOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity }}>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 32,
          transform: `scale(${Math.min(contentScale, 1)})`,
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 60,
              height: 60,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            }}
          >
            <svg width="36" height="36" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ fontSize: 48, fontWeight: 700, color: 'white' }}>Arakis</span>
        </div>

        {/* Big stat */}
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 80, fontWeight: 800, color: '#22c55e', margin: 0 }}>100+</p>
          <p style={{ fontSize: 28, color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>Hours Saved Per Review</p>
        </div>

        {/* CTA */}
        <div
          style={{
            padding: '18px 56px',
            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            borderRadius: 14,
            fontSize: 22,
            fontWeight: 700,
            color: 'white',
            boxShadow: '0 20px 60px rgba(34, 197, 94, 0.4)',
            opacity: interpolate(frame, [30, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Save Your Time Now
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const TimeSaverVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0f', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Sequence from={0} durationInFrames={90}>
        <TimeSaverIntro />
      </Sequence>
      <Sequence from={90} durationInFrames={180}>
        <ChatScene />
      </Sequence>
      <Sequence from={270} durationInFrames={450}>
        <WorkflowScene />
      </Sequence>
      <Sequence from={720} durationInFrames={120}>
        <OutputScene />
      </Sequence>
      <Sequence from={840} durationInFrames={60}>
        <TimeSaverOutro />
      </Sequence>
    </AbsoluteFill>
  );
};
