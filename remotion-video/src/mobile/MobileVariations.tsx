import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

// ============= TIME SAVER HOOK =============
export const MobileTimeSaverIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1Opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const strikethrough = interpolate(frame, [20, 40], [0, 100], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const line2Opacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const line2Scale = spring({ frame: frame - 35, fps, config: { damping: 8, stiffness: 80 } });
  const logoOpacity = interpolate(frame, [55, 70], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40 }}>
        <div style={{ opacity: line1Opacity, position: 'relative', textAlign: 'center' }}>
          <span style={{ fontSize: 36, color: 'rgba(255, 255, 255, 0.5)', fontWeight: 500 }}>
            Weeks of
            <br />
            manual review
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

        <div style={{ opacity: line2Opacity, transform: `scale(${Math.max(0, Math.min(line2Scale, 1.1))})`, textAlign: 'center' }}>
          <span
            style={{
              fontSize: 56,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #22c55e 0%, #10b981 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            5 Minutes
            <br />
            with AI
          </span>
        </div>

        <div style={{ opacity: logoOpacity, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="30" height="30" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ fontSize: 32, color: 'white', fontWeight: 600 }}>Arakis</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const MobileTimeSaverOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32, transform: `scale(${Math.min(contentScale, 1)})` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="32" height="32" viewBox="0 0 60 60" fill="white"><path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" /></svg>
          </div>
          <span style={{ fontSize: 40, fontWeight: 700, color: 'white' }}>Arakis</span>
        </div>
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 72, fontWeight: 800, color: '#22c55e', margin: 0 }}>100+</p>
          <p style={{ fontSize: 22, color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>Hours Saved</p>
        </div>
        <div
          style={{
            padding: '18px 48px',
            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            borderRadius: 14,
            fontSize: 20,
            fontWeight: 700,
            color: 'white',
            opacity: interpolate(frame, [30, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Save Your Time
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============= COST EFFECTIVE HOOK =============
export const MobileCostEffectiveIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const traditionalOpacity = interpolate(frame, [15, 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const traditionalCost = Math.floor(interpolate(frame, [25, 45], [0, 15000], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const vsOpacity = interpolate(frame, [40, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const arakisOpacity = interpolate(frame, [50, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const arakisScale = spring({ frame: frame - 50, fps, config: { damping: 10, stiffness: 80 } });
  const badgeOpacity = interpolate(frame, [65, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <div style={{ opacity: titleOpacity }}>
          <span style={{ fontSize: 24, color: 'rgba(255, 255, 255, 0.6)', fontWeight: 500 }}>Systematic Review Costs</span>
        </div>

        <div style={{ opacity: traditionalOpacity, textAlign: 'center' }}>
          <p style={{ fontSize: 48, fontWeight: 700, color: '#ef4444', margin: 0 }}>${traditionalCost.toLocaleString()}</p>
          <p style={{ fontSize: 16, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 4 }}>Traditional Agency</p>
        </div>

        <div style={{ opacity: vsOpacity, width: 50, height: 50, borderRadius: '50%', backgroundColor: 'rgba(255, 255, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 18, fontWeight: 700, color: 'rgba(255, 255, 255, 0.7)' }}>VS</span>
        </div>

        <div style={{ opacity: arakisOpacity, transform: `scale(${Math.max(0, Math.min(arakisScale, 1.1))})`, textAlign: 'center' }}>
          <p style={{ fontSize: 72, fontWeight: 800, color: '#22c55e', margin: 0 }}>$5</p>
          <p style={{ fontSize: 16, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 4 }}>With Arakis AI</p>
        </div>

        <div
          style={{
            opacity: badgeOpacity,
            padding: '10px 20px',
            backgroundColor: 'rgba(34, 197, 94, 0.2)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: 10,
          }}
        >
          <span style={{ fontSize: 18, color: '#22c55e', fontWeight: 600 }}>Save 99.97%</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const MobileCostEffectiveOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, transform: `scale(${Math.min(contentScale, 1)})` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="32" height="32" viewBox="0 0 60 60" fill="white"><path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" /></svg>
          </div>
          <span style={{ fontSize: 40, fontWeight: 700, color: 'white' }}>Arakis</span>
        </div>
        <p style={{ fontSize: 22, color: 'rgba(255, 255, 255, 0.8)', margin: 0, textAlign: 'center', lineHeight: 1.4 }}>
          Professional reviews
          <br />
          <span style={{ color: '#22c55e' }}>without the price tag</span>
        </p>
        <div
          style={{
            padding: '18px 48px',
            background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
            borderRadius: 14,
            fontSize: 20,
            fontWeight: 700,
            color: 'white',
            opacity: interpolate(frame, [30, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Start for $5
        </div>
        <p style={{ margin: 0, fontSize: 14, color: 'rgba(255, 255, 255, 0.5)', opacity: interpolate(frame, [40, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
          No subscription required
        </p>
      </div>
    </AbsoluteFill>
  );
};

// ============= ACADEMIC HOOK =============
export const MobileAcademicIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const journalsOpacity = interpolate(frame, [15, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const messageOpacity = interpolate(frame, [35, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const messageScale = spring({ frame: frame - 35, fps, config: { damping: 10, stiffness: 80 } });
  const badgeOpacity = interpolate(frame, [55, 65], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const logoOpacity = interpolate(frame, [65, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const exitOpacity = interpolate(frame, [80, 90], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const journals = ['Nature', 'Lancet', 'JAMA', 'BMJ'];

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: exitOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}>
        <div style={{ opacity: titleOpacity }}>
          <span style={{ fontSize: 22, color: 'rgba(255, 255, 255, 0.5)', fontWeight: 400, letterSpacing: 3 }}>READY FOR</span>
        </div>

        <div style={{ opacity: journalsOpacity, display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          {journals.map((journal, i) => (
            <div
              key={journal}
              style={{
                opacity: interpolate(frame, [20 + i * 4, 30 + i * 4], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                padding: '8px 16px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <span style={{ fontSize: 16, color: 'rgba(255, 255, 255, 0.7)', fontStyle: 'italic' }}>{journal}</span>
            </div>
          ))}
        </div>

        <div style={{ opacity: messageOpacity, transform: `scale(${Math.max(0, Math.min(messageScale, 1))})`, textAlign: 'center' }}>
          <span
            style={{
              fontSize: 40,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #f59e0b 0%, #eab308 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              lineHeight: 1.2,
            }}
          >
            Publication
            <br />
            Ready
          </span>
        </div>

        <div
          style={{
            opacity: badgeOpacity,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 16px',
            backgroundColor: 'rgba(139, 92, 246, 0.15)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            borderRadius: 10,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
            <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span style={{ fontSize: 14, color: '#a855f7', fontWeight: 600 }}>PRISMA 2020</span>
        </div>

        <div style={{ opacity: logoOpacity, display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="24" height="24" viewBox="0 0 60 60" fill="white"><path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" /></svg>
          </div>
          <span style={{ fontSize: 26, color: 'white', fontWeight: 600 }}>Arakis</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const MobileAcademicOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  const features = ['Forest Plots', 'PRISMA', 'APA 7'];

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, transform: `scale(${Math.min(contentScale, 1)})` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="32" height="32" viewBox="0 0 60 60" fill="white"><path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" /></svg>
          </div>
          <span style={{ fontSize: 40, fontWeight: 700, color: 'white' }}>Arakis</span>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          {features.map((f, i) => (
            <div
              key={f}
              style={{
                opacity: interpolate(frame, [15 + i * 5, 25 + i * 5], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                padding: '8px 16px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: 8,
                fontSize: 14,
                color: 'rgba(255, 255, 255, 0.8)',
              }}
            >
              {f}
            </div>
          ))}
        </div>

        <div
          style={{
            padding: '18px 48px',
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            borderRadius: 14,
            fontSize: 20,
            fontWeight: 700,
            color: 'white',
            opacity: interpolate(frame, [35, 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Publish Faster
        </div>
        <p style={{ margin: 0, fontSize: 15, color: 'rgba(255, 255, 255, 0.5)', opacity: interpolate(frame, [45, 55], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
          Journal-ready in minutes
        </p>
      </div>
    </AbsoluteFill>
  );
};
