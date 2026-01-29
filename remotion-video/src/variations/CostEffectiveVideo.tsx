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

// Hook: Cost comparison angle
const CostEffectiveIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });

  // Traditional cost animation
  const traditionalOpacity = interpolate(frame, [15, 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Count up animation for traditional cost
  const traditionalCost = Math.floor(interpolate(frame, [25, 50], [0, 15000], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));

  // VS animation
  const vsOpacity = interpolate(frame, [40, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const vsScale = spring({ frame: frame - 40, fps, config: { damping: 8, stiffness: 100 } });

  // Arakis cost
  const arakisOpacity = interpolate(frame, [50, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const arakisScale = spring({ frame: frame - 50, fps, config: { damping: 10, stiffness: 80 } });

  const subtitleOpacity = interpolate(frame, [65, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}>
        {/* Title */}
        <div style={{ opacity: titleOpacity, marginBottom: 20 }}>
          <span style={{ fontSize: 32, color: 'rgba(255, 255, 255, 0.6)', fontWeight: 500 }}>
            Systematic Review Costs
          </span>
        </div>

        {/* Cost comparison */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 60 }}>
          {/* Traditional */}
          <div style={{ opacity: traditionalOpacity, textAlign: 'center' }}>
            <p style={{ fontSize: 56, fontWeight: 700, color: '#ef4444', margin: 0 }}>
              ${traditionalCost.toLocaleString()}
            </p>
            <p style={{ fontSize: 18, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 8 }}>
              Traditional Agency
            </p>
          </div>

          {/* VS */}
          <div
            style={{
              opacity: vsOpacity,
              transform: `scale(${Math.max(0, Math.min(vsScale, 1))})`,
              width: 60,
              height: 60,
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ fontSize: 20, fontWeight: 700, color: 'rgba(255, 255, 255, 0.7)' }}>VS</span>
          </div>

          {/* Arakis */}
          <div
            style={{
              opacity: arakisOpacity,
              transform: `scale(${Math.max(0, Math.min(arakisScale, 1.1))})`,
              textAlign: 'center',
            }}
          >
            <p style={{ fontSize: 72, fontWeight: 800, color: '#22c55e', margin: 0 }}>$5</p>
            <p style={{ fontSize: 18, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 8 }}>
              With Arakis AI
            </p>
          </div>
        </div>

        {/* Savings badge */}
        <div
          style={{
            opacity: subtitleOpacity,
            marginTop: 20,
            padding: '12px 24px',
            backgroundColor: 'rgba(34, 197, 94, 0.2)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: 12,
          }}
        >
          <span style={{ fontSize: 20, color: '#22c55e', fontWeight: 600 }}>Save 99.97%</span>
        </div>
      </div>

      {/* Money icons */}
      {[...Array(8)].map((_, i) => {
        const x = 10 + (i * 12);
        const startFrame = 5 + i * 3;
        const opacity = interpolate(frame, [startFrame, startFrame + 15, 75, 85], [0, 0.2, 0.2, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const y = interpolate(frame, [startFrame, 90], [100 - i * 5, 90 - i * 5], { extrapolateRight: 'clamp' });

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${y}%`,
              opacity,
              fontSize: 32,
            }}
          >
            💰
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// CTA: Start cheap
const CostEffectiveOutro: React.FC = () => {
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

        {/* Tagline */}
        <p style={{ fontSize: 28, color: 'rgba(255, 255, 255, 0.8)', margin: 0, textAlign: 'center' }}>
          Professional systematic reviews
          <br />
          <span style={{ color: '#22c55e' }}>without the professional price tag</span>
        </p>

        {/* CTA */}
        <div
          style={{
            padding: '18px 56px',
            background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
            borderRadius: 14,
            fontSize: 22,
            fontWeight: 700,
            color: 'white',
            boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            opacity: interpolate(frame, [30, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Start for Just $5
        </div>

        {/* Trust badge */}
        <div
          style={{
            opacity: interpolate(frame, [40, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
            color: 'rgba(255, 255, 255, 0.5)',
            fontSize: 14,
          }}
        >
          No subscription required • Pay per review
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CostEffectiveVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0f', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Sequence from={0} durationInFrames={90}>
        <CostEffectiveIntro />
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
        <CostEffectiveOutro />
      </Sequence>
    </AbsoluteFill>
  );
};
