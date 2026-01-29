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

// Hook: Academic excellence angle
const AcademicIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const titleY = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });

  // Journal logos fade in
  const journalsOpacity = interpolate(frame, [20, 35], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Main message
  const messageOpacity = interpolate(frame, [40, 55], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const messageScale = spring({ frame: frame - 40, fps, config: { damping: 10, stiffness: 80 } });

  // PRISMA badge
  const badgeOpacity = interpolate(frame, [55, 65], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Logo
  const logoOpacity = interpolate(frame, [65, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const journals = ['Nature', 'Lancet', 'JAMA', 'BMJ', 'NEJM'];

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        {/* Title */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${(1 - Math.min(titleY, 1)) * 20}px)`,
          }}
        >
          <span style={{ fontSize: 28, color: 'rgba(255, 255, 255, 0.5)', fontWeight: 400, letterSpacing: 4 }}>
            READY FOR
          </span>
        </div>

        {/* Journal names scrolling */}
        <div style={{ opacity: journalsOpacity, display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
          {journals.map((journal, i) => {
            const delay = i * 5;
            const journalOpacity = interpolate(frame, [25 + delay, 35 + delay], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={journal}
                style={{
                  opacity: journalOpacity,
                  padding: '8px 20px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: 8,
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}
              >
                <span style={{ fontSize: 18, color: 'rgba(255, 255, 255, 0.7)', fontWeight: 500, fontStyle: 'italic' }}>
                  {journal}
                </span>
              </div>
            );
          })}
        </div>

        {/* Main message */}
        <div
          style={{
            opacity: messageOpacity,
            transform: `scale(${Math.max(0, Math.min(messageScale, 1))})`,
            marginTop: 16,
          }}
        >
          <span
            style={{
              fontSize: 56,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #f59e0b 0%, #eab308 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Publication-Ready Reviews
          </span>
        </div>

        {/* PRISMA badge */}
        <div
          style={{
            opacity: badgeOpacity,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 20px',
            backgroundColor: 'rgba(139, 92, 246, 0.15)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            borderRadius: 10,
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
            <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span style={{ fontSize: 16, color: '#a855f7', fontWeight: 600 }}>PRISMA 2020 Compliant</span>
        </div>

        {/* Logo */}
        <div style={{ opacity: logoOpacity, display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="26" height="26" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ fontSize: 28, color: 'white', fontWeight: 600 }}>Arakis</span>
        </div>
      </div>

      {/* Floating academic icons */}
      <div
        style={{
          position: 'absolute',
          top: '12%',
          left: '8%',
          opacity: interpolate(frame, [15, 30, 75, 85], [0, 0.2, 0.2, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
        }}
      >
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="1.5">
          <path d="M12 14l9-5-9-5-9 5 9 5z" />
          <path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
        </svg>
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: '15%',
          right: '10%',
          opacity: interpolate(frame, [25, 40, 75, 85], [0, 0.2, 0.2, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
        }}
      >
        <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="1.5">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
    </AbsoluteFill>
  );
};

// CTA: Publish faster
const AcademicOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  const features = [
    { icon: '📊', label: 'Forest & Funnel Plots' },
    { icon: '📋', label: 'PRISMA Flow Diagrams' },
    { icon: '📝', label: 'Full Manuscript' },
    { icon: '📚', label: 'APA 7 References' },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity }}>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 28,
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

        {/* Features */}
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 600 }}>
          {features.map((feature, i) => {
            const featureOpacity = interpolate(frame, [15 + i * 5, 25 + i * 5], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={feature.label}
                style={{
                  opacity: featureOpacity,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: 8,
                }}
              >
                <span style={{ fontSize: 18 }}>{feature.icon}</span>
                <span style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.8)' }}>{feature.label}</span>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div
          style={{
            padding: '18px 56px',
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            borderRadius: 14,
            fontSize: 22,
            fontWeight: 700,
            color: 'white',
            boxShadow: '0 20px 60px rgba(245, 158, 11, 0.4)',
            opacity: interpolate(frame, [35, 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Publish Faster with AI
        </div>

        {/* Subtitle */}
        <p
          style={{
            margin: 0,
            fontSize: 16,
            color: 'rgba(255, 255, 255, 0.5)',
            opacity: interpolate(frame, [45, 55], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Journal-ready in minutes, not months
        </p>
      </div>
    </AbsoluteFill>
  );
};

export const AcademicVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0f', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Sequence from={0} durationInFrames={90}>
        <AcademicIntro />
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
        <AcademicOutro />
      </Sequence>
    </AbsoluteFill>
  );
};
